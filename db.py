import sqlite3
from pathlib import Path

# このPythonファイルと同じ場所にDBファイルを作る
DB_PATH = Path(__file__).resolve().parent / "search_cache.db"


# SQLiteに接続する関数
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# 検索結果保存用のテーブルを作る関数
def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id TEXT NOT NULL,
                site TEXT NOT NULL,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                url TEXT,
                image TEXT
            )
        """)

# 保存用テーブルに保存するデータの関数
def save_results(search_id, products):
    with get_connection() as conn:
        for product in products:
            conn.execute(
                """
                INSERT INTO search_results
                (search_id, site, name, price, url, image)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    search_id,
                    product["site"],
                    product["name"],
                    product["price"],
                    product["url"],
                    product["image"],
                ),
            )

# search_idを指定して保存データを取得する関数
def get_results(search_id):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM search_results
            WHERE search_id = ?
            ORDER BY price
            """,
            (search_id,),
        ).fetchall()
    return rows

# 指定した検索結果の総件数を取得
def count_results(search_id):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM search_results
            WHERE search_id = ?
            """,
            (search_id,),
        ).fetchone()

    return row[0]


# 指定したページの商品だけ取得
def get_results_page(search_id, page, page_size, sort="price_asc"):
    # 安い順・高い順をSQL用に変換
    order = "DESC" if sort == "price_desc" else "ASC"

    # 何件飛ばして取得を始めるか
    offset = (page - 1) * page_size

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT site, name, price, url, image
            FROM search_results
            WHERE search_id = ?
            ORDER BY price {order}
            LIMIT ? OFFSET ?
            """,
            (search_id, page_size, offset),
        ).fetchall()

    return [dict(row) for row in rows]

# データベース作成命令
if __name__ == "__main__":
    init_db()

    print("データベースを作成しました")
