import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "ecom.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE(user_id, product_id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            discount_amount REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            payment_txn_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
            [
                ("alice", "password123", "alice@example.com"),
                ("bob", "password456", "bob@example.com"),
                ("testuser", "test1234", "test@example.com"),
            ],
        )

    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        products = [
            ("iPhone 15", "electronics", 7999.0, 50, "Apple smartphone"),
            ("MacBook Pro", "electronics", 14999.0, 20, "Apple laptop"),
            ("AirPods Pro", "electronics", 1899.0, 100, "Wireless earbuds"),
            ("Nike Air Max", "clothing", 899.0, 80, "Running shoes"),
            ("Adidas Hoodie", "clothing", 499.0, 60, "Sports hoodie"),
            ("Levi's Jeans", "clothing", 599.0, 45, "Classic denim"),
            ("Python Cookbook", "books", 89.0, 200, "Python programming guide"),
            ("Clean Code", "books", 79.0, 150, "Software craftsmanship"),
            ("Coffee Maker", "home", 399.0, 30, "Automatic coffee machine"),
            ("Desk Lamp", "home", 129.0, 75, "LED desk lamp"),
        ]
        cursor.executemany(
            "INSERT INTO products (name, category, price, stock, description) VALUES (?, ?, ?, ?, ?)",
            products,
        )

    _migrate(conn)
    conn.commit()
    conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()}
    if "discount_amount" not in cols:
        conn.execute("ALTER TABLE orders ADD COLUMN discount_amount REAL NOT NULL DEFAULT 0")
    if "payment_txn_id" not in cols:
        conn.execute("ALTER TABLE orders ADD COLUMN payment_txn_id TEXT")
