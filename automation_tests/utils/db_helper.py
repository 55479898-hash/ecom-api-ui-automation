"""Database assertion helper — SQLite by default, PyMySQL when TEST_ENV=staging + mysql config."""

import os
import sqlite3
from pathlib import Path

try:
    import pymysql
except ImportError:
    pymysql = None

from utils.config_loader import load_env_config


class DbHelper:
    def __init__(self, config: dict | None = None):
        self.config = config or load_env_config()
        self.db_type = self.config.get("db_type", "sqlite")

    def _sqlite_path(self) -> Path:
        base = Path(__file__).parent.parent
        return (base / self.config["db_path"]).resolve()

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        if self.db_type == "mysql" and pymysql:
            conn = pymysql.connect(
                host=self.config["db_host"],
                port=self.config.get("db_port", 3306),
                user=self.config["db_user"],
                password=self.config["db_password"],
                database=self.config["db_name"],
                cursorclass=pymysql.cursors.DictCursor,
            )
            try:
                with conn.cursor() as cur:
                    cur.execute(sql.replace("?", "%s"), params)
                    return cur.fetchone()
            finally:
                conn.close()
        conn = sqlite3.connect(self._sqlite_path())
        conn.row_factory = sqlite3.Row
        row = conn.execute(sql, params).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_order(self, order_id: int) -> dict | None:
        return self.query_one(
            "SELECT id, user_id, total_amount, discount_amount, status, payment_txn_id FROM orders WHERE id = ?",
            (order_id,),
        )

    def get_product_stock(self, product_id: int) -> int:
        row = self.query_one("SELECT stock FROM products WHERE id = ?", (product_id,))
        return row["stock"] if row else -1

    def count_cart_items(self, user_id: int) -> int:
        row = self.query_one(
            "SELECT COUNT(*) AS cnt FROM cart_items WHERE user_id = ?",
            (user_id,),
        )
        return row["cnt"] if row else 0

    def clear_cart(self, user_id: int) -> None:
        if self.db_type == "mysql":
            raise NotImplementedError("clear_cart for mysql in demo env")
        conn = sqlite3.connect(self._sqlite_path())
        conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    def set_product_stock(self, product_id: int, stock: int) -> None:
        if self.db_type == "mysql":
            raise NotImplementedError("set_product_stock for mysql in demo env")
        conn = sqlite3.connect(self._sqlite_path())
        conn.execute("UPDATE products SET stock = ? WHERE id = ?", (stock, product_id))
        conn.commit()
        conn.close()
