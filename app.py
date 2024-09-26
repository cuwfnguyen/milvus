import os
from flask import Flask, request, jsonify
from openai import OpenAI
from pymilvus import connections, Collection, WeightedRanker, AnnSearchRequest
from functools import lru_cache
import threading
import queue
import logging.config
from langchain_milvus.utils.sparse import BM25SparseEmbedding
import helps

app = Flask(__name__)
embedding_queue = queue.Queue()
logging.config.fileConfig('logging.config')

connections.connect(host=os.getenv('milvus_host'), port=os.getenv('milvus_port'))
collection = Collection(os.getenv('collection_name'))

def add_to_milvus(content):
    embedding_queue.put(content)

@lru_cache(maxsize=1000)
def get_embedding(text):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

def get_sparse_embedding(content):
    content = helps.preprocess(content)
    sparse_embedding_func = BM25SparseEmbedding(corpus=[content])
    return sparse_embedding_func.embed_documents([content])[0]

def embedding_worker():
    while True:
        content = embedding_queue.get()
        if content is None:
            break
        entity = {
            "dense_vector": get_embedding(content),
            "sparse_vector": get_sparse_embedding(content),
            "content": content,
        }
        collection.insert([entity])
        # collection.load()
        embedding_queue.task_done()

def hybrid_search(data):
    query = data.get('content')
    weight = data.get('weight') if data.get('weight') else 1
    top_k = data.get('limit') if data.get('limit') else 5
    reqs = build_hybrid_search_params(query, top_k)
    rerank = WeightedRanker(weight, 1-weight)
    res = collection.hybrid_search(reqs, rerank, limit=top_k, output_fields=["id","content"])
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
            "params": {"ef": 250},
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
    results = hybrid_search(data)
    response = []
    for hit in results[0]:
        response.append({
            'content': hit.entity.get('content'),
            'score': hit.distance
        })
    return jsonify({
        "response": response
    }), 200

worker_thread = None

def start_worker():
    global worker_thread
    worker_thread = threading.Thread(target=embedding_worker)
    worker_thread.start()

def cleanup():
    if worker_thread:
        embedding_queue.put(None)
        worker_thread.join()
    collection.release()
    connections.disconnect('default')

import atexit
atexit.register(cleanup)

