from app import app, embedding_knowledge_thread, scheduler
from kafka_consumer import kafka_thread
import logging
from flask import g

@app.before_request
def start_background_threads():
    try:
        embedding_knowledge_thread.start()
        kafka_thread.start()
        scheduler.start()
        g.background_threads_started = True
    except Exception as e:
        logging.info(f"Error starting threads: {str(e)}")

if __name__ == "__main__":
    app.run(debug=True)