# Milvus Service Integration

## Description

This embedding vector service provides APIs for integrating, including embedding knowledge and product

## Key Features

- Embedding Knowledge, vector search, hybrid search with the external applications.
- Embedding Product name, vector search, hybrid search
- Data of product insert via Kafka consumer 
- RESTful API: Provides API for interacting with the service from external applications.

## Docker Milvus Installation

To install Milvus using Docker, follow the instructions below:

- Official Milvus documentation:  
  [https://milvus.io/docs/install_standalone-docker-compose.md](https://milvus.io/docs/install_standalone-docker-compose.md)

- Run the following command to start Milvus standalone using Docker Compose:

  ```bash
  docker-compose -f https://github.com/milvus-io/milvus/releases/download/v2.2.6/milvus-standalone-docker-compose.yml up -d

## Install Attu DB Admin

https://github.com/zilliztech/attu

## Project Structure

```plaintext
milvus_service/
│
├── data/
│   ├── .env
│   └── script.txt
│
├── source/
│   ├── app.py
│   ├── config.py
│   ├── helps.py
│   ├── kafka_consumer.py
│   ├── postgres_connect.py
│   └── wsgi.py
│
├── .gitignore
├── README.md
└── requirements.txt

```

## Running this Project

- Install project dependencies by running:
    ```bash
    pip install -r requirement.txt
- To run the server using Gunicorn:
  ```bash
  gunicorn -w 4 -b host:8181 wsgi:app

- To shutdown the server running on port 8181:
    ```bash
  kill -9 $(lsof -t -i:8181)

## API Usage

- To insert data into the knowledge base, use the following curl command:
    ```bash
  curl --location 'http://host:8181/knowledge/insert' \
    --header 'Content-Type: application/json' \
    --data '{
        "content": ["OpenAI là một công ty công nghệ về AI", "Google DeepMind DeepMind là một nhánh AI của Google, nổi tiếng với việc phát triển AI trong nhiều lĩnh vực, bao gồm cả mô hình ngôn ngữ. DeepMind đã tạo ra các mô hình như Chinchilla và Gopher, nhằm cải thiện khả năng hiểu ngôn ngữ tự nhiên và phản hồi thông minh hơn. Ngoài ra, DeepMind còn đóng góp vào việc phát triển các hệ thống AI thông minh trong các lĩnh vực như y tế và trò chơi. Họ cũng phát triển các giải pháp học sâu và học tăng cường."]
    }'
- To search for data in the knowledge base, use the following curl command:
    ```bash
  curl --location 'http://host:8181/knowledge/search' \
    --header 'Content-Type: application/json' \
    --data '{
        "content": "Open AI là gì",
        "limit": 3,
        "weight: (optional)
    }'
- To search for product_name in product_product, use the following cURL command:
  ```bash
  curl --location 'http://host:8181/product/search' \
  --header 'Content-Type: application/json' \
  --data '{
      "content": "Son dưỡng",
      "limit": 5,
      "weight: 1
  }'
if score > score_config: return one record, else return top_k = limit



