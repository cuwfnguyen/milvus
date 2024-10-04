import config
from kafka import KafkaConsumer
import json
from datetime import datetime
import os
import postgres_connect

consumer_topic = os.getenv('kafka_topic')
bootstrap_servers = os.getenv('kafka_server')

consumer = KafkaConsumer(
    topic=consumer_topic,
    bootstrap_servers=[bootstrap_servers],
    auto_offset_reset='earliest',
    enable_auto_commit=True)

def pare_data_consumer():
    for message in consumer:
        msg = message.value
        json_string = msg.decode('utf-8')
        json_data = json.loads(json_string)
        process_and_insert_data(json_data)

def process_and_insert_data(data):
    product_query = """
        INSERT INTO products (
            id, alias, page_id, category_id, item_name, item_id, description,
            item_sku, image, min_price, max_price, last_updated, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        ) ON CONFLICT (id, page_id) DO UPDATE SET
            alias = EXCLUDED.alias,
            category_id = EXCLUDED.category_id,
            item_name = EXCLUDED.item_name,
            item_id = EXCLUDED.item_id,
            description = EXCLUDED.description,
            item_sku = EXCLUDED.item_sku,
            image = EXCLUDED.image,
            min_price = EXCLUDED.min_price,
            max_price = EXCLUDED.max_price,
            last_updated = EXCLUDED.last_updated,
            updated_at = NOW()
        RETURNING id;
    """

    record = postgres_connect.execute_insert_update(product_query, (
        data['id'], data['alias'], data['page_id'], data['category_id'],
        data['item_name'], data['item_id'], data['description'],
        data['item_sku'], data['image'], data['min_price'],
        data['max_price'], datetime.fromtimestamp(data['last_updated'])
    ))

    product_id = record[0]

    variation_query = """
        INSERT INTO variations (
            product_id, variation_name, variation_sku, variation_id,
            variation_price, variation_stock, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, NOW(), NOW()
        ) ON CONFLICT (variation_id, product_id) DO UPDATE SET
            variation_name = EXCLUDED.variation_name,
            variation_sku = EXCLUDED.variation_sku,
            variation_price = EXCLUDED.variation_price,
            variation_stock = EXCLUDED.variation_stock,
            updated_at = NOW();
    """

    for variation in data['variations']:
        postgres_connect.execute_insert_update(variation_query, (
            product_id, variation['variation_name'],
            variation['variation_sku'], variation['variation_id'],
            variation['variation_price'], variation['variation_stock']
        ))
