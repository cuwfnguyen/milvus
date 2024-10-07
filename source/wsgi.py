from app import app, embedding_knowledge_thread, scheduler
from kafka_consumer import kafka_thread

if __name__ == "__main__":
    embedding_knowledge_thread.start()
    kafka_thread.start()
    scheduler.start()
    app.run(debug=True)