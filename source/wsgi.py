from app import app, embedding_knowledge_thread, scheduler
from kafka_consumer import kafka_thread

@app.before_first_request
def start_background_threads():
    embedding_knowledge_thread.start()
    kafka_thread.start()
    scheduler.start()

if __name__ == "__main__":
    app.run(debug=True)