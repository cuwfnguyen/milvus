import config
import os
from flask import Flask, request, jsonify
from openai import OpenAI
from pymilvus import connections, Collection, WeightedRanker, AnnSearchRequest
from functools import lru_cache
import threading
import queue
from langchain_milvus.utils.sparse import BM25SparseEmbedding
import helps
from apscheduler.schedulers.background import BackgroundScheduler
import postgres_connect

app = Flask(__name__)
embedding_queue = queue.Queue()
MINUTES_UPDATE_PRODUCT_EMBEDDING = 1

connections.connect(host=os.getenv('milvus_host'), port=os.getenv('milvus_port'))
collection_knowledge = Collection(os.getenv('collection_knowledge'))
collection_product = Collection(os.getenv('collection_product'))

def add_to_milvus(content):
    embedding_queue.put(content)

@lru_cache(maxsize=1000)
def get_embedding(text):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

@lru_cache(maxsize=1000)
def get_sparse_embedding(content):
    content = helps.preprocess(content)
    sparse_embedding_func = BM25SparseEmbedding(corpus=[content])
    return sparse_embedding_func.embed_documents([content])[0]

def embedding_knowledge():
    while True:
        content = embedding_queue.get()
        if content is None:
            break
        entity = {
            "dense_vector": get_embedding(content),
            "sparse_vector": get_sparse_embedding(content),
            "content": content,
        }
        collection_knowledge.insert([entity])
        embedding_queue.task_done()

def hybrid_search(data, collection):
    query = data.get('content')
    weight = data.get('weight') if data.get('weight') else 1
    top_k = data.get('limit') if data.get('limit') else 5
    reqs = build_hybrid_search_params(query, top_k)
    rerank = WeightedRanker(weight, 1-weight)
    if collection == 'collection_knowledge':
        res = collection_knowledge.hybrid_search(reqs, rerank, limit=top_k, output_fields=["id","content"])
    else:
        res = collection_product.hybrid_search(reqs, rerank, limit=top_k, output_fields=["product_id", "product_name"])
    return res

def build_hybrid_search_params(query, top_k):
    sparse_vector = get_sparse_embedding(query)
    search_param_0 = {
        "data": [sparse_vector],
        "anns_field": "sparse_vector",
        "param": {
            "metric_type": "IP",
            "params": {}
        },
        "limit": top_k
    }
    request_1 = AnnSearchRequest(**search_param_0)

    dense_vector = get_embedding(query)
    search_param_1 = {
        "data": [dense_vector],
        "anns_field": "dense_vector",
        "param": {
            "metric_type": "COSINE",
            "params": {"ef": 400},
        },
        "limit": top_k
    }
    request_2 = AnnSearchRequest(**search_param_1)
    reqs = [request_2, request_1]
    return reqs

@app.route('/knowledge/insert', methods=['POST'])
def insert_document():
    data = request.json
    list_content = data.get('content')
    for content in list_content:
        add_to_milvus(content)
    return jsonify({"status": "success"}), 200

@app.route('/knowledge/search', methods=['POST'])
def search_document():
    data = request.json
    results = hybrid_search(data, 'collection_knowledge')
    response = []
    for hit in results[0]:
        response.append({
            'content': hit.entity.get('content'),
            'score': hit.distance
        })
    return jsonify({
        "response": response
    }), 200

def insert_embedding_product():
    query = f"""SELECT item_name as product_name, item_id as product_id, 'shopee' as channel, page_id 
            FROM products 
            WHERE updated_at >= NOW() - INTERVAL '{MINUTES_UPDATE_PRODUCT_EMBEDDING} minutes'"""
    product_update = postgres_connect.execute_query(query)
    list_update = []
    for data in product_update:
        entity = {
            "dense_vector": get_embedding(data.get('product_name')),
            "sparse_vector": get_sparse_embedding(data.get('product_name')),
            "product_id": str(data.get('product_id')),
            "channel": data.get('channel'),
            "page_id": data.get("page_id"),
            "product_name": data.get("product_name")
        }
        list_update.append(entity)
    if list_update:
        collection_product.upsert(list_update)

@app.route('/product/search', methods=['POST'])
def search_product():
    data = request.json
    results = hybrid_search(data, 'collection_product')
    product_ids = []
    for hit in results[0]:
        if hit.distance > os.getenv('distant_product_search'):
            return jsonify({
                "response": get_meta_data_product([hit.entity.get('product_id')])
            }), 200
        product_ids.append(hit.entity.get('product_id'))
    return jsonify({
        "response": get_meta_data_product(product_ids)
    }), 200

def get_meta_data_product(product_ids):
    if len(product_ids) == 1:
        query = f" select item_name, description from products where item_id = ({product_ids[0]}"
    else:
        product_ids_placeholder = ', '.join([str(p_id) for p_id in product_ids])
        query = f"SELECT item_name, description FROM products WHERE item_id IN ({product_ids_placeholder})"
    data = postgres_connect.execute_query(query)
    return data

scheduler = BackgroundScheduler()
scheduler.add_job(insert_embedding_product, 'interval', minutes=MINUTES_UPDATE_PRODUCT_EMBEDDING)
embedding_knowledge_thread = threading.Thread(target=embedding_knowledge)

