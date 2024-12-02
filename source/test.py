from kafka import KafkaProducer
import config
import os
import json
from app import collection_search
consumer_topic = os.getenv('KAFKA_PRODUCT_TOPIC')
bootstrap_servers = os.getenv('KAFKA_SERVER').replace('"', '').split(',')

producer = KafkaProducer(
    bootstrap_servers=bootstrap_servers,
    api_version=(0, 10, 1)
)

# Gửi dữ liệu vào topic
topic = consumer_topic
data = {"alias":"cunx_test",
    "category_id":0,
    "item_name":"Khăn quàng mùa đông ấm áp",
    "item_id":123332299,
    "description":"Khăn quàng mùa đông ấm áp",
    "item_stock":0,
    "variations":[
        {
            "variation_name":"Màu xanh",
            "variation_sku":"test13214627",
            "variation_id":123332299,
            "variation_price":200000.0000,
            "variation_stock":0.0
        },
        {
            "variation_name":"Màu đỏ",
            "variation_sku":"test1231",
            "variation_id":12333229922,
            "variation_price":200000.0000,
            "variation_stock":31.0
        }
    ],
    "last_updated":1732507762,
    "type":"social"
}


if __name__ == "__main__":

    json_data = json.dumps(data).encode('utf-8')
    producer.send(topic, value=json_data)
    producer.flush()  # Đảm bảo dữ liệu đã được gửi
    print(f"Message sent to topic '{topic}'!")
#     data = {
#     "page_id": "marketv3-sapostaging",
#     "channel": "facebook",
#     "content": "Ốp lưng",
#     "limit": 5,
#     "task": "description"
#
# }