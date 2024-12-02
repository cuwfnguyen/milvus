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
import postgres_connect
import logging.config
import logging

app = Flask(__name__)
embedding_queue = queue.Queue()
MINUTES_UPDATE_PRODUCT_EMBEDDING = 2

logging.config.fileConfig(config.get_config_file('logging.cfg'))

connections.connect(host=os.getenv('MILVUS_HOST'), port=os.getenv('MILVUS_PORT'))
collection_knowledge = Collection(os.getenv('MILVUS_COLLECTION_KNOWLEDGE'))
collection_product = Collection(os.getenv('MILVUS_COLLECTION_PRODUCT'))
collection_faq = Collection(os.getenv('MILVUS_COLLECTION_FAQ'))

def add_to_milvus(content):
    embedding_queue.put(content)
    print("import queue")

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

def delete_milvus_record(field_name, record_ids):
    try:
        collection_faq.delete(f"{field_name} in {record_ids}")
    except Exception as e:
        print(e)

def embedding_knowledge():
    while True:
        data = embedding_queue.get()
        if data:
            print("valid data")
            if data.get('type') == "faq":
                question = data.get("question")
                entity = {
                    "id": data.get('id'),
                    "dense_vector": get_embedding(question),
                    "sparse_vector": get_sparse_embedding(question),
                    "question": question,
                    "answer": data.get('answer'),
                    "channel": data.get("channel"),
                    "chatbot_id": data.get("chatbot_id")
                }
                collection_faq.upsert([entity])
                print("insert faq")
            elif data.get('type') == 'knowledge':
                content = data.get('content')
                entity = {
                    "dense_vector": get_embedding(content),
                    "sparse_vector": get_sparse_embedding(content),
                    "content": content,
                    "channel": data.get('channel')
                }
                collection_knowledge.insert([entity])
                print("insert knowledge")
            embedding_queue.task_done()

def collection_search(data, collection):
    query = data.get('content')
    weight = float(data.get('weight')) if data.get('weight') else 1
    top_k = data.get('limit') if data.get('limit') else 5
    dense_vector = get_embedding(query)
    if weight not in [0,1]:
        sparse_vector = get_sparse_embedding(query)
        reqs = build_hybrid_search_params(sparse_vector, dense_vector, top_k)
        rerank = WeightedRanker(weight, 1-weight)
        if collection == 'collection_knowledge':
            res = collection_knowledge.hybrid_search(reqs, rerank, limit=top_k, output_fields=["id","content"])
        else:
            res = collection_product.hybrid_search(reqs, rerank, limit=top_k, output_fields=["product_id", "product_name"])
    else:
        vector_search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 400}
        }
        if collection == 'collection_knowledge':
            res = collection_knowledge.search(data=[dense_vector], anns_field='dense_vector', param= vector_search_params, limit=top_k, output_fields=["id", "content"])
        elif collection == 'collection_faq':
            chatbot_id = data.get('chatbot_id')
            res = collection_faq.search(data=[dense_vector], anns_field='dense_vector', param= vector_search_params, limit=top_k , expr=f"chatbot_id =='{chatbot_id}'", output_fields=["id", "question", "answer"])
        else:
            channel = data.get("channel")
            page_id = data.get('page_id')
            res = collection_product.search(data=[dense_vector], anns_field='dense_vector', param= vector_search_params, limit=top_k,  expr=f"page_id =='{page_id}' and channel=='{channel}'", output_fields=["product_id", "product_name"])
    return res

def build_hybrid_search_params(sparse_vector, dense_vector, top_k):

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

@app.route('/api/milvus/knowledge/insert', methods=['POST'])
def insert_knowledge():
    data = request.json
    list_content = data.get('content')
    for content in list_content:
        knowledge_format = {
            "type": "knowledge",
            "content": content,
            "channel": data.get("channel")
        }
        add_to_milvus(knowledge_format)
    return jsonify({"status": "success"}), 200

@app.route('/api/milvus/knowledge/search', methods=['POST'])
def search_document():
    data = request.json
    results = collection_search(data, 'collection_knowledge')
    response = []
    for hit in results[0]:
        response.append({
            'content': hit.entity.get('content'),
            'score': hit.distance
        })
    return jsonify({
        "response": response
    }), 200

@app.route('/api/milvus/product/search', methods=['POST'])
def search_product():
    data = request.json
    if not data.get('content') or not data.get('page_id') or data.get('channel') not in ['facebook', 'shopee'] or data.get('task') not in ['stock', 'description']:
        return jsonify({
            "response": "Invalid request body"
        }), 200
    results = collection_search(data, 'collection_product')
    product_ids = []
    for hit in results[0]:
        product_id = hit.entity.get('product_id').split('_')[2]
        if hit.distance > float(os.getenv('MILVUS_DISTANT_PRODUCT_SEARCH')):
            return jsonify({
                "response": get_meta_data_product([product_id], data.get('task'), data.get('channel'))
            }), 200
        elif hit.distance > 0.5:
            product_ids.append(int(product_id))
    return jsonify({
        "response": get_meta_data_product(product_ids, data.get('task'), data.get('channel'))
    }), 200

@app.route('/api/milvus/faq/insert', methods=['POST'])
def insert_faq():
    data = request.json
    list_content = data.get('content')
    for content in list_content:
        faq_format = {
            "type": "faq",
            "question": content.get("question"),
            "answer": content.get("answer"),
            "channel": data.get("channel"),
            "chatbot_id": data.get("chatbot_id")
        }
        add_to_milvus(faq_format)
    return jsonify({"status": "success"}), 200

@app.route('/api/milvus/faq/search', methods=['POST'])
def search_faq():
    data = request.json
    if not data.get('content') or not data.get('chatbot_id'):
        return jsonify({
            "response": "content and chatbot_id are required"
        }), 200
    results = collection_search(data, 'collection_faq')
    response = []
    for hit in results[0]:
        response.append({
            'question': hit.entity.get('question'),
            'answer': hit.entity.get('answer'),
            'score': hit.distance
        })
    return jsonify({
        "response": response
    }), 200

def get_meta_data_product(product_ids, task, channel):
    if not product_ids:
        return 'Không tìm ra sản phẩm'

    if len(product_ids) == 1:
        if task == 'description':
            query = f" select item_name as product_name, description as product_description from products where item_id = {product_ids[0]} and source_type = '{channel}'"
            data = postgres_connect.execute_query(query)
        else:

            query_variation = f"""
                       SELECT p.item_name AS product_name,
                                v.variation_name,
                                v.variation_stock quantity
                            FROM
                                products
                                p INNER JOIN variations v ON v.product_id = p.item_id and v.source_type = p.source_type
                            WHERE
                                1 = 1 
                            AND p.item_id = {product_ids[0]};
                        """
            data = postgres_connect.execute_query(query_variation)
            if not data:
                query_product = f" select item_name product_name, item_stock quantity from products where item_id = {product_ids[0]} and source_type = '{channel}'"
                data = postgres_connect.execute_query(query_product)
    else:
        product_ids_placeholder = ', '.join([str(p_id) for p_id in product_ids])
        query = f"""
        WITH ordered_products AS (
          SELECT item_name, description, 
                 ARRAY_POSITION(ARRAY{product_ids}, item_id) AS order_index
          FROM products
          WHERE item_id IN ({product_ids_placeholder}) and source_type = '{channel}'
        )
        SELECT item_name as product_name
        FROM ordered_products
        ORDER BY order_index;
        """
        data = postgres_connect.execute_query(query)
    return data

embedding_knowledge_thread = threading.Thread(target=embedding_knowledge, daemon=True)

