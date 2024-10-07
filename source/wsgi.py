from app import app, embedding_knowledge_thread, scheduler,insert_embedding_product
from kafka_consumer import kafka_thread

if __name__ == "__main__":
    embedding_knowledge_thread.start()
    kafka_thread.start()
    scheduler.start()
    app.run(debug=True)
    # insert_embedding_product()