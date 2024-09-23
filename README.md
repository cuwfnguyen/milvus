# Docker Milvus Setup and Running the Project

## Docker Milvus Installation

To install Milvus using Docker, follow the instructions below:

- Official Milvus documentation:  
  [https://milvus.io/docs/install_standalone-docker-compose.md](https://milvus.io/docs/install_standalone-docker-compose.md)

- Run the following command to start Milvus standalone using Docker Compose:

  ```bash
  docker-compose -f https://github.com/milvus-io/milvus/releases/download/v2.2.6/milvus-standalone-docker-compose.yml up -d

##Install Attu DB Admin
-   To install and run Attu, a DB admin interface for Milvus:
    ```bash
    docker run -p 8000:3000 -e HOST_URL=host:8181 -e MILVUS_URL=host:19530 zilliz/attu:latest

##Project Structure

```plaintext
milvus_service/
├── .env
├── .gitignore
├── app.log
├── app.py
├── logging.config
├── README.md
├── requirements.txt
└── wsgi.py
```

##Running this Project
- Install project dependencies by running:
    ```bash
    pip install -r requirement.txt
- To run the server using Gunicorn:
  ```bash
  gunicorn -w 4 -b host:8181 wsgi:app
- Viewing Logs
    ```bash
  tail -n 0 -f app.log
- To shutdown the server running on port 8181:
    ```bash
  kill -9 $(lsof -t -i:8181)
  
##API Usage
- To insert data into the knowledge base, use the following curl command:
    ```bash
  curl --location 'http://localhost:8181/knowledge/insert' \
    --header 'Content-Type: application/json' \
    --data '{
        "content": [
        
        ]
    }'
- To search for data in the knowledge base, use the following curl command:
    ```bash
  curl --location 'http://localhost:8181/knowledge/search' \
    --header 'Content-Type: application/json' \
    --data '{
        "content": "Open AI là gì",
        "limit": 3
    }'



