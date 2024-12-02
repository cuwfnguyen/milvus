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
  
## Install Attu DB Admin

https://github.com/zilliztech/attu

## Project Structure

```plaintext
milvus_service/
│
├── data/
│   └── .env
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
    curl --location 'http://192.168.12.99:8085/knowledge/insert' \
  --header 'Content-Type: application/json' \
  --data '{   "channel": "shopee",
      "content": [
          "[Thay đổi địa chỉ ngành hàng] [Vận chuyển] Tôi có thể thay đổi thông tin số điện thoại/địa chỉ nhận hàng sau khi đã đặt hàng không?\nBạn chỉ có thể thay đổi thông tin số điện thoại / địa chỉ nhận hàng sau khi đã đặt hàng nếu đáp ứng đủ những yêu cầu sau:\nNgười bán chưa thực hiện việc xác nhận đơn hàng (Đơn hàng chưa có mã vận đơn)\nBạn chưa từng thực hiện yêu cầu thay đổi thông tin số điện thoại/địa chỉ nhận hàng cho đơn hàng này. Với mỗi đơn hàng, bạn chỉ có thể thay đổi thông tin số điện thoại/địa chỉ nhận hàng một lần duy nhất.\nVới yêu cầu thay đổi địa chỉ nhận hàng:\n+ Địa chỉ nhận hàng mới phải nằm trong khu vực hoạt động được hỗ trợ của phương thức vận chuyển đã lựa chọn\n+ Việc thay đổi địa chỉ nhận hàng mới không làm thay đổi mức phí vận chuyển dự kiến của đơn hàng\nNếu đáp ứng đầy đủ tất cả yêu cầu trên, bạn có thể tự thực hiện yêu cầu thay đổi thông tin số điện thoại/địa chỉ nhận hàng."
      ]
  }'
- To search data in the knowledge base, use the following curl command:
    ```bash
  curl --location 'http://host:8181/knowledge/search' \
    --header 'Content-Type: application/json' \
    --data '{
        "content": "Open AI là gì",
        "limit": 3,
        "weight: (optional)
    }'
  
- To search stock data for product_name in product_product, use the following cURL command:
  ```bash
  curl --location '192.168.12.99:8085/product/search' \
  --header 'Content-Type: application/json' \
  --data '{
      "channel": "shopee",
      "page_id"
      "content": "Nước hoa Fragona",
      "limit": 5,
      "task": "stock"
  }'
  
- To search description data for product_name in product_product, use the following cURL command:
  ```bash
  curl --location '192.168.12.99:8085/product/search' \
  --header 'Content-Type: application/json' \
  --data '{
      "channel": "shopee"
      "page_id":
      "content": "Nước hoa Fragona",
      "limit": 5,
      "task": "description"
  }'
  
 - Note: 

  if score > score_config (0.9): return one record, else return top_k = limit

  For the stock task, return the number of product variants if the original product has variants, otherwise return the quantity of that product.
  
  channel must be a value of facebook, shopee

  task must be a value of description or stock

- To search data in the faq, use the following curl command:
    ```bash
    curl --location 'http://192.168.12.99:8085/faq/search' \
  --header 'Content-Type: application/json' \
  --data '{   
      "chatbot_id": "",
      "content": "Thời gian bảo hành là bao lâu?",
      "limit": 3
  }'




