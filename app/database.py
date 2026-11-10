import mysql.connector
from mysql.connector import pooling
from flask import current_app

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="price_tracker_pool",
            pool_size=5,
            pool_reset_session=True,
            **current_app.config["MYSQL_CONFIG"]
        )
    return _pool

def get_connection():
    return get_pool().get_connection()

def fetch_all(query, params=()):
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        if cur:
            cur.close()
        conn.close()

def fetch_one(query, params=()):
    rows = fetch_all(query, params)
    return rows[0] if rows else None

def execute(query, params=()):
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur.lastrowid, cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        conn.close()
