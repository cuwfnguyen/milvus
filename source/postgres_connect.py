import config
import psycopg2
from psycopg2 import pool
import os
from psycopg2.extras import DictCursor
import logging

connection_pool = pool.ThreadedConnectionPool(
    1,
    5,
    host=os.getenv('POSTGRES_HOST'),
    port=os.getenv('POSTGRES_PORT'),
    database=os.getenv('POSTGRES_DB'),
    user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD')
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
            if isinstance(params, list):
                cur.executemany(query, params)
            else:
                cur.execute(query, params)
            conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        logging.info(f"Database error: {e}")
        raise
    finally:
        release_db_connection(conn)

def execute_delete(query, params=None):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query, params)
            conn.commit()
            return cur.rowcount
    except psycopg2.Error as e:
        conn.rollback()
        logging.info(f"Database error: {e}")
        raise
    finally:
        release_db_connection(conn)

