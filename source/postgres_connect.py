import config
import psycopg2
from psycopg2 import pool
import os
from psycopg2.extras import DictCursor
import logging
from tqdm import tqdm
from base import get_embedding
import random

connection_pool = pool.ThreadedConnectionPool(
    1,
    5,
    host=os.getenv('db_host'),
    port=os.getenv('db_port'),
    database=os.getenv('db_name'),
    user=os.getenv('db_user'),
    password=os.getenv('db_password')
)

def get_db_connection():
    return connection_pool.getconn()

def release_db_connection(conn):
    connection_pool.putconn(conn)

def execute_query(query, params=None):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query, params)
            conn.commit()
            results = cur.fetchall()
            return [dict(row) for row in results]
    except psycopg2.Error as e:
        conn.rollback()
        logging.info(f"Database error: {e}")
        raise
    finally:
        release_db_connection(conn)

def execute_insert_update(query, params=None):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query, params)
            conn.commit()
            return cur.fetchone()
    except psycopg2.Error as e:
        conn.rollback()
        logging.info(f"Database error: {e}")
        raise
    finally:
        release_db_connection(conn)
