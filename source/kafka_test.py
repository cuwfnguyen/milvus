import config
from kafka import KafkaConsumer
import json
from datetime import datetime
import os
import postgres_connect
import threading

consumer_topic = os.getenv('kafka_topic')
bootstrap_servers = os.getenv('kafka_server')

consumer = KafkaConsumer(
    consumer_topic,
    bootstrap_servers=[bootstrap_servers],
    auto_offset_reset='earliest',
    enable_auto_commit=True)

def pare_data_consumer():
    for message in consumer:
        print(message.value)

if __name__ == "__main__":
    pare_data_consumer()