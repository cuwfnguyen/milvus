import config
from kafka import KafkaConsumer
import json
from datetime import datetime
import os
import postgres_connect
import threading
import time

consumer_topic = os.getenv('kafka_topic')
bootstrap_servers = os.getenv('kafka_server')

consumer = KafkaConsumer(
    consumer_topic,
    bootstrap_servers=[bootstrap_servers],
    auto_offset_reset='earliest',
    enable_auto_commit=True)

def pare_data_consumer():
    try:
        while True:
            for message in consumer:
                msg = message.value
                json_string = msg.decode('utf-8')
                json_data = json.loads(json_string)
                process_and_insert_data(json_data)
    except Exception as e:
        print(f"Lỗi khi tiêu thụ Kafka: {e}")
        time.sleep(5)

def process_and_insert_data(data):
    product_query = """
        INSERT INTO products (
            id, alias, page_id, category_id, item_name, item_id, description,
            item_sku, image, min_price, max_price, last_updated
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (item_id, page_id) DO UPDATE SET
            alias = EXCLUDED.alias,
            category_id = EXCLUDED.category_id,
            item_name = EXCLUDED.item_name,
            item_id = EXCLUDED.item_id,
            description = EXCLUDED.description,
            item_sku = EXCLUDED.item_sku,
            image = EXCLUDED.image,
            min_price = EXCLUDED.min_price,
            max_price = EXCLUDED.max_price,
            last_updated = EXCLUDED.last_updated
        RETURNING item_id;
    """

    record = postgres_connect.execute_insert_update(product_query, (
        data.get('id'), data.get('alias'), data.get('page_id'), data.get('category_id'),
        data.get('item_name'), data.get('item_id'), data.get('description'),
        data.get('item_sku'), data.get('image'), data.get('min_price'),
        data.get('max_price'), datetime.fromtimestamp(data.get('last_updated', 0))
    ))

    product_id = record[0]

    variation_query = """
        INSERT INTO variations (
            product_id, variation_name, variation_sku, variation_id,
            variation_price, variation_stock
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (variation_id, product_id) DO UPDATE SET
            variation_name = EXCLUDED.variation_name,
            variation_sku = EXCLUDED.variation_sku,
            variation_price = EXCLUDED.variation_price,
            variation_stock = EXCLUDED.variation_stock
        RETURNING variation_id;
    """
    if data.get('variations'):
        for variation in data.get('variations'):
            postgres_connect.execute_insert_update(variation_query, (
                product_id, variation['variation_name'],
                variation['variation_sku'], variation['variation_id'],
                variation['variation_price'], variation['variation_stock']
            ))

kafka_thread = threading.Thread(target=pare_data_consumer)
