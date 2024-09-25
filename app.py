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
        collection.load()
        embedding_queue.task_done()

def hybrid_search(query, weight, top_k = 3):
    reqs = build_hybrid_search_params(query, top_k)
    rerank = WeightedRanker(0.8, 0.2)
    res = collection.hybrid_search(reqs,rerank,limit=top_k)
    print(res)
    return []

def build_hybrid_search_params(query, top_k):
    sparse_vector = get_sparse_embedding(query)
    sparse_params = {
        "data": sparse_vector,
        "anns_field": "dense_vector",
        "param": {
            "metric_type": "IP"
        },
        "limit": top_k
    }
    request_1 = AnnSearchRequest(**sparse_params)

    dense_vector = get_embedding(query)
    dense_params = {
        "data": dense_vector,
        "anns_field": "posterVector",
        "param": {
            "metric_type": "COSINE"
        },
        "limit": top_k
    }
    request_2 = AnnSearchRequest(**dense_params)
    reqs = [request_1, request_2]
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
    content = data.get('content')
    results = hybrid_search(query=content, weight=1, top_k=data.get('limit'))
    response = []
    for hit in results:
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

# import atexit
# atexit.register(cleanup)

if __name__ == "__main__":
    start_worker()
    app.run(host=os.getenv('host'), port=os.getenv('port'), debug=True)