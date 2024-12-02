import config
from kafka import KafkaConsumer
import json
from datetime import datetime
import os
import postgres_connect
import threading
import time

consumer_topic = os.getenv('KAFKA_PRODUCT_TOPIC')
bootstrap_servers = os.getenv('KAFKA_SERVER').replace('"', '').split(',')
offset_reset = os.getenv('KAFKA_PRODUCT_OFFSET')
BATCH_SIZE = 100

consumer = KafkaConsumer(
    consumer_topic,
    bootstrap_servers=bootstrap_servers,
    enable_auto_commit=True,
    auto_offset_reset=offset_reset,
    api_version=(0, 10, 1),
    max_poll_records=BATCH_SIZE * 2,
    group_id='ai_consumer_db_product'
)


def pare_data_consumer():
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
            if len(buffer) >= BATCH_SIZE or (current_time - last_batch_time >= 20):
                process_batch(buffer)
                buffer.clear()
                last_batch_time = current_time
        except Exception as e:
            print(f"Milvus Consumer Error: {e}")
            time.sleep(5)


def process_batch(messages):
    products = []
    for message in messages:
        try:
            json_string = message.decode('utf-8')
            json_data = json.loads(json_string)
            if json_data.get('type') == 'social':
                json_data['page_id'] = json_data.get('alias')
                json_data['source_type'] = 'facebook'
            elif json_data.get('id'):
                json_data['source_type'] = 'shopee'
            products.append(json_data)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"Invalid message format: {e}")
        except Exception as e:
            print(f"Error processing message: {e}")
    if products:
        process_and_insert_data(products)


def process_and_insert_data(data_list):
    try:
        product_query = """
            INSERT INTO products (
                id, alias, page_id, category_id, item_name, item_id, description,
                item_sku, image, min_price, max_price, item_stock, source_type, last_updated
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (item_id, page_id, source_type) DO UPDATE SET
                category_id = EXCLUDED.category_id,
                item_name = EXCLUDED.item_name,
                item_id = EXCLUDED.item_id,
                description = EXCLUDED.description,
                item_sku = EXCLUDED.item_sku,
                image = EXCLUDED.image,
                min_price = EXCLUDED.min_price,
                max_price = EXCLUDED.max_price,
                item_stock = EXCLUDED.item_stock,
                last_updated = EXCLUDED.last_updated
        """

        variation_query = """
                   INSERT INTO variations (
                       product_id, variation_name, variation_sku, variation_id,
                       variation_price, variation_stock, source_type
                   ) VALUES (
                       %s, %s, %s, %s, %s, %s, %s
                   ) ON CONFLICT (variation_id, product_id, source_type) DO UPDATE SET
                       variation_name = EXCLUDED.variation_name,
                       variation_sku = EXCLUDED.variation_sku,
                       variation_price = EXCLUDED.variation_price,
                       variation_stock = EXCLUDED.variation_stock
               """

        product_params = [
            (
                data.get('id'), data.get('alias'), data.get('page_id'), data.get('category_id'),
                data.get('item_name'), data.get('item_id'), data.get('description'),
                data.get('item_sku'), str(data.get('image')), data.get('min_price'),
                data.get('max_price'), data.get('item_stock', 0), data.get('source_type'),
                datetime.fromtimestamp(data.get('last_updated', 0))
            ) for data in data_list
        ]
        postgres_connect.execute_insert_update(product_query, product_params)

        variation_params = []
        for data in data_list:
            if data.get('variations'):
                for variation in data.get('variations'):
                    variation_params.append((
                        data.get('item_id'),
                        variation.get('variation_name'),
                        variation.get('variation_sku'),
                        variation.get('variation_id'),
                        variation.get('variation_price'),
                        variation.get('variation_stock'),
                        data.get('source_type')
                    ))
        postgres_connect.execute_insert_update(variation_query, variation_params)

    except Exception as e:
        print(f"Product insert error: {str(e)}")


kafka_product_thread = threading.Thread(target=pare_data_consumer, daemon=True)
