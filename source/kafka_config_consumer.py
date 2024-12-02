import config
from kafka import KafkaConsumer
import json
import os
import postgres_connect
import time
import app
import threading

consumer_topic = os.getenv('KAFKA_CONFIG_TOPIC')
bootstrap_servers = os.getenv('KAFKA_SERVER').replace('"', '').split(',')

consumer = KafkaConsumer(
    consumer_topic,
    bootstrap_servers=bootstrap_servers,
    group_id='ai_consumer_config_bot',
    enable_auto_commit=True,
    auto_offset_reset='latest',
    api_version=(0, 10, 1))


def pare_data_consumer():
    try:
        while True:
            for message in consumer:
                msg = message.value
                json_string = msg.decode('utf-8')
                json_data = json.loads(json_string)
                save_data(json_data)
    except Exception as e:
        print(f"Lỗi khi tiêu thụ Kafka: {e}")
        time.sleep(5)

def save_data(data):
    event = data.get('event_type')
    print(event)
    if event == 'CREATE_AI_CHATBOT':
        save_chatbot_style(data['payload'].get('chatbot'))
        channel_type = data['payload']['chatbot'].get('channel_type')
        save_chatbot_faq(data['payload'].get('scenarios'), channel_type)
    elif event in ["CREATE_AI_CHATBOT_SCENARIO", "UPDATE_AI_CHATBOT_SCENARIO"]:
        channel_type = get_channel_type_chatbot(data['payload'].get('chabot_id'))
        if channel_type:
            save_chatbot_faq([data['payload'].get('scenario')], channel_type)
    elif event == "UPDATE_AI_CHATBOT":
        save_chatbot_style(data['payload'].get('chatbot'))
    elif event == "DELETE_AI_CHATBOT_SCENARIO":
        app.delete_milvus_record('id', [data['payload'].get('scenario_id')])
    elif event == "DELETE_AI_CHATBOT":
        delete_chatbot(data['payload'].get('chatbot_id'))

def delete_chatbot(chatbot_id):
    delete_query = f"""
        delete from chatbot_data 
        where id = '{chatbot_id}'
    """
    postgres_connect.execute_delete(delete_query)
    app.delete_milvus_record('chatbot_id', [chatbot_id])

def get_channel_type_chatbot(chatbot_id):
    chatbot_query = f"select channel_type from chatbot_data where id = '{chatbot_id}'"
    data = postgres_connect.execute_query(chatbot_query)
    if data:
        return data[0].get('channel_type')
    else:
        return ''

def save_chatbot_faq(data, channel_type):
    for case in data:
        if case.get('scenario_type') == 'SYSTEM':
            insert_query = """
                INSERT INTO agent_config (id, store_id, chatbot_id, topic, scenario_description, handler, scenario_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    store_id = EXCLUDED.store_id,
                    chatbot_id = EXCLUDED.chatbot_id,
                    topic = EXCLUDED.topic,
                    scenario_description = EXCLUDED.scenario_description,
                    handler = EXCLUDED.handler,
                    scenario_type = EXCLUDED.scenario_type
                RETURNING id;
            """

            postgres_connect.execute_insert_update(insert_query,
                                                   (case.get("id"), case.get("store_id"), case.get("chatbot_id"),
                                                    case.get("topic"), case.get("scenario_description"),
                                                    case.get("handler"), case.get("scenario_type")))

        else:
            faq_format = {
                "type": "faq",
                "id": case.get("id"),
                "question": case.get("scenario"),
                "answer": case.get("scenario_description"),
                "channel": channel_type.lower(),
                "chatbot_id": case.get("chatbot_id")
            }
            app.add_to_milvus(faq_format)

def save_chatbot_style(data):
    insert_query = """
        INSERT INTO chatbot_data (id, store_id, channel_type, page_ids, name, description, chatbot_style, business_type, response_type, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id, channel_type) DO UPDATE SET
                store_id = EXCLUDED.store_id,
                description = EXCLUDED.description,
                page_ids = EXCLUDED.page_ids,
                chatbot_style = EXCLUDED.chatbot_style,
                business_type = EXCLUDED.business_type,
                response_type = EXCLUDED.response_type,
                status = EXCLUDED.status
        RETURNING id;
    """
    postgres_connect.execute_insert_update(insert_query, (
        data.get("id"), data.get("store_id"), data.get("channel_type"), data.get('page_ids'),
        data.get("name"), data.get("description"), data.get("chatbot_style"),
        data.get("business_type"), data.get("response_type"), data.get("status")
    ))


kafka_config_thread = threading.Thread(target=pare_data_consumer, daemon=True)