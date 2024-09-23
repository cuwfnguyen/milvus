import os
from flask import Flask, request, jsonify
from openai import OpenAI
from pymilvus import connections, Collection
from functools import lru_cache
import threading
import queue



app = Flask(__name__)
embedding_queue = queue.Queue()

connections.connect(host=os.getenv('milvus_host'), port=os.getenv('milvus_port'))
collection = Collection('knowledge_base')
collection.load()

@lru_cache(maxsize=1000)
def get_embedding(text):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

def add_to_milvus(content):
    embedding_queue.put(content)

def embedding_worker():
    while True:
        content = embedding_queue.get()
        if content is None:
            break
        embedding = get_embedding(content)
        collection.insert([{"content": content, "embedding_vector": embedding}])
        embedding_queue.task_done()

def search_in_milvus(query, top_k=2):
    query_embedding = get_embedding(query)
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    results = collection.search(
        data=[query_embedding],
        anns_field="embedding_vector",
        param=search_params,
        limit=top_k,
        output_fields=["content"]
    )
    return results[0]

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
    results = search_in_milvus(query = content, top_k = data.get('limit'))
    response = []
    for hit in results:
        response.append({
            'content': hit.entity.get('content'),
            'score': hit.distance
        })
    return jsonify({
        "response": response
    }), 200

if __name__ == '__main__':
    worker_thread = threading.Thread(target=embedding_worker)
    worker_thread.start()
    app.run(host=os.getenv('host'), port=os.getenv('port'), debug=True)


