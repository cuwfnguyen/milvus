from app import app, embedding_knowledge_thread
from kafka_product_consumer import kafka_product_thread
from kafka_config_consumer import kafka_config_thread
from vector_database_consumer import vectordb_product_thread
import logging

background_threads_started = False

def start_background_threads():
    global background_threads_started
    if not background_threads_started:
        try:
            embedding_knowledge_thread.start()
            vectordb_product_thread.start()
            kafka_product_thread.start()
            kafka_config_thread.start()
            background_threads_started = True
            logging.info("Background threads started successfully")
        except Exception as e:
            logging.error(f"Error starting threads: {str(e)}")

start_background_threads()