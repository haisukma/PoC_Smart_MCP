import os
import mysql.connector
import re
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """
    Membuat koneksi ke database MySQL.
    """

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )

BLOCKED_TABLES = ["inventory_products"]

def get_database_schema():
    """
    Mengambil informasi tabel dan kolom dari database, kecuali tabel inventory_products.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE,
            COLUMN_KEY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """

    cursor.execute(
        query,
        (os.getenv("DB_NAME"),)
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    schema = {}

    for row in rows:
        table_name = row["TABLE_NAME"]

        if table_name not in schema:
            schema[table_name] = []

        schema[table_name].append({
            "column": row["COLUMN_NAME"],
            "type": row["DATA_TYPE"],
            "key": row["COLUMN_KEY"]
        })

    # schema = {}
    # for row in rows:
    #     table_name = row["TABLE_NAME"]

    #     if table_name.lower() in [t.lower() for t in BLOCKED_TABLES]:
    #         continue

    #     if table_name not in schema:
    #         schema[table_name] = []

    #     schema[table_name].append(
    #         {
    #             "column": row["COLUMN_NAME"],
    #             "type": row["DATA_TYPE"],
    #             "key": row["COLUMN_KEY"],
    #         }
    #     )

    return schema

def execute_read_query(query: str):
    """
    Menjalankan query SQL read-only.
    Hanya SELECT yang diperbolehkan.
    """

    query_clean = query.strip()

    if not query_clean.lower().startswith("select"):
        raise ValueError(
            "Query ditolak. Hanya query SELECT yang diperbolehkan."
        )

    # for blocked_table in BLOCKED_TABLES:
    #     pattern = r"\b" + re.escape(blocked_table) + r"\b"
    #     if re.search(pattern, query_clean, re.IGNORECASE):
    #         raise ValueError(
    #             f"Akses ditolak! Tabel '{blocked_table}' bersifat rahasia dan tidak boleh diakses."
    #         )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute(query_clean)

        results = cursor.fetchall()

        return results

    finally:

        cursor.close()
        conn.close()