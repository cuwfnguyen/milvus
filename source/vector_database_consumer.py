import config
import threading
from kafka import KafkaConsumer
import os
import json
import time
from app import get_embedding, get_sparse_embedding, collection_product

consumer_topic = os.getenv('KAFKA_PRODUCT_TOPIC')
bootstrap_servers = os.getenv('KAFKA_SERVER').replace('"', '').split(',')
BATCH_SIZE = 50
offset_reset = os.getenv('KAFKA_PRODUCT_OFFSET')

consumer = KafkaConsumer(
    consumer_topic,
    bootstrap_servers=bootstrap_servers,
    enable_auto_commit=True,
    auto_offset_reset=offset_reset,
    api_version=(0, 10, 1),
    max_poll_records=BATCH_SIZE * 2,
    group_id='ai_consumer_vectordb_product'
)


def process_batch(messages):
    product_upsert = []
    for msg in messages:
        try:
            json_string = msg.decode('utf-8')
            json_data = json.loads(json_string)
            if json_data.get('type') == 'social':
                json_data['page_id'] = json_data.get('alias')
                json_data['source_type'] = 'facebook'
            elif json_data.get('id'):
                json_data['source_type'] = 'shopee'
            if json_data.get('source_type') and json_data.get('item_name') and json_data.get(
                    'page_id') and json_data.get('item_id'):
                entity = {
                    "dense_vector": get_embedding(json_data.get('item_name')),
                    "sparse_vector": get_sparse_embedding(json_data.get('item_name')),
                    "product_id": json_data.get('source_type') + '_' + json_data.get('page_id') + '_' + str(
                        json_data.get('item_id')),
                    "channel": json_data.get('source_type'),
                    "page_id": json_data.get("page_id"),
                    "product_name": json_data.get("item_name")
                }
                product_upsert.append(entity)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"Invalid message format: {e}")
        except Exception as e:
            print(f"Error processing message: {e}")
    if product_upsert:
        try:
            collection_product.upsert(product_upsert)
        except Exception as e:
            print(f"Error processing product insert milvus: {e}")
        print('product insert batch 50')


def milvus_pare_data_consumer():
    buffer = []
    last_batch_time = time.time()

    while True:
        try:
            msg_batch = consumer.poll(timeout_ms=1000)
            if msg_batch:
                for tp, messages in msg_batch.items():
                    for message in messages:
                        if message and message.value:
                            buffer.append(message.value)
            current_time = time.time()
            if len(buffer) >= BATCH_SIZE or (current_time - last_batch_time >= 30):
                process_batch(buffer)
                buffer.clear()
                last_batch_time = current_time
        except Exception as e:
            print(f"Milvus Consumer Error: {e}")
            time.sleep(5)


vectordb_product_thread = threading.Thread(target=milvus_pare_data_consumer, daemon=True)