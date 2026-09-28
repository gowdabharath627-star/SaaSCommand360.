"""
SaaSCommand 360 - Database Manager for PostgreSQL (Neon / pgAdmin) & SQLite
Supports:
1. Neon Serverless PostgreSQL (Cloud, Free Tier)
2. Local PostgreSQL (pgAdmin 4)
3. Local SQLite (Offline fallback)
"""

import os
import sqlite3
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, "warehouse", "saascommand360.db")

def is_postgres():
    return bool(DATABASE_URL and (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")))

def get_connection():
    """Returns a connection to PostgreSQL (Neon/Local) if configured, else SQLite."""
    if is_postgres():
        # Clean postgresql:// prefix if formatted as postgres://
        conn_str = DATABASE_URL
        if conn_str.startswith("postgres://"):
            conn_str = "postgresql://" + conn_str[len("postgres://"):]
        return psycopg2.connect(conn_str)
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(query, params=None, fetch="all"):
    """Executes a query and returns dicts."""
    conn = get_connection()
    try:
        if is_postgres():
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params or ())
                if fetch == "all":
                    res = cur.fetchall()
                    return [dict(r) for r in res]
                elif fetch == "one":
                    res = cur.fetchone()
                    return dict(res) if res else None
                else:
                    conn.commit()
                    return None
        else:
            cur = conn.cursor()
            cur.execute(query, params or ())
            if fetch == "all":
                res = cur.fetchall()
                return [dict(r) for r in res]
            elif fetch == "one":
                res = cur.fetchone()
                return dict(res) if res else None
            else:
                conn.commit()
                return None
    finally:
        conn.close()

def init_postgres_schema():
    """Executes schema_postgres.sql on PostgreSQL / Neon."""
    if not is_postgres():
        print("DATABASE_URL is not set to a PostgreSQL connection string. Please check .env.")
        return False
    
    schema_path = os.path.join(PROJECT_ROOT, "warehouse", "schema_postgres.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        ddl = f.read()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            print("Applying PostgreSQL Star Schema DDL to Neon / pgAdmin database...")
            cur.execute(ddl)
            conn.commit()
        print("Schema successfully applied to PostgreSQL!")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error applying PostgreSQL schema: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    if "--init" in sys.argv:
        init_postgres_schema()
    else:
        print(f"PostgreSQL Active: {is_postgres()}")
        if is_postgres():
            parsed = urlparse(DATABASE_URL)
            print(f"Connected to host: {parsed.hostname}, db: {parsed.path[1:]}")
        else:
            print(f"Using local SQLite fallback: {SQLITE_DB_PATH}")
