import hashlib
import secrets
from datetime import datetime, timezone

from database import get_connection

_active_tokens: dict[str, int] = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate_user(username: str, password: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, password, email FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    if row["password"] != password:
        return None
    return {"id": row["id"], "username": row["username"], "email": row["email"]}


def create_token(user_id: int) -> str:
    token = secrets.token_hex(16)
    _active_tokens[token] = user_id
    return token


def get_user_id_from_token(token: str | None) -> int | None:
    if not token:
        return None
    return _active_tokens.get(token)


def revoke_token(token: str) -> None:
    _active_tokens.pop(token, None)


def search_products(
    q: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
) -> list[dict]:
    conn = get_connection()
    query = "SELECT id, name, category, price, stock, description FROM products WHERE 1=1"
    params: list = []

    if q:
        query += " AND (name LIKE ? OR description LIKE ?)"
        pattern = f"%{q}%"
        params.extend([pattern, pattern])
    if category:
        query += " AND category = ?"
        params.append(category.lower())
    if min_price is not None:
        query += " AND price >= ?"
        params.append(min_price)
    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)

    query += " ORDER BY id"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_to_cart(user_id: int, product_id: int, quantity: int) -> dict:
    conn = get_connection()
    product = conn.execute(
        "SELECT id, stock FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if product is None:
        conn.close()
        return {"success": False, "message": "Product not found", "error_code": "PRODUCT_NOT_FOUND"}

    if product["stock"] < quantity:
        conn.close()
        return {"success": False, "message": "Insufficient stock", "error_code": "INSUFFICIENT_STOCK"}

    existing = conn.execute(
        "SELECT id, quantity FROM cart_items WHERE user_id = ? AND product_id = ?",
        (user_id, product_id),
    ).fetchone()

    if existing:
        new_qty = existing["quantity"] + quantity
        if new_qty > product["stock"]:
            conn.close()
            return {"success": False, "message": "Insufficient stock", "error_code": "INSUFFICIENT_STOCK"}
        conn.execute(
            "UPDATE cart_items SET quantity = ? WHERE id = ?",
            (new_qty, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)",
            (user_id, product_id, quantity),
        )

    conn.commit()
    conn.close()
    return {"success": True, "message": "Added to cart"}


def get_cart(user_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT ci.product_id, ci.quantity, p.name, p.price, p.stock
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.id
        WHERE ci.user_id = ?
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def clear_cart(user_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def create_order(user_id: int) -> dict:
    conn = get_connection()
    cart = conn.execute(
        """
        SELECT ci.product_id, ci.quantity, p.name, p.price, p.stock
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.id
        WHERE ci.user_id = ?
        """,
        (user_id,),
    ).fetchall()

    if not cart:
        conn.close()
        return {"success": False, "message": "Cart is empty", "error_code": "EMPTY_CART"}

    subtotal = 0.0
    for item in cart:
        if item["quantity"] > item["stock"]:
            conn.close()
            return {
                "success": False,
                "message": f"Insufficient stock for {item['name']}",
                "error_code": "INSUFFICIENT_STOCK",
            }
        subtotal += item["price"] * item["quantity"]

    discount = round(subtotal * 0.1, 2) if subtotal >= 100 else 0.0
    total = round(subtotal - discount, 2)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.execute(
        "INSERT INTO orders (user_id, total_amount, discount_amount, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
        (user_id, total, discount, now),
    )
    order_id = cursor.lastrowid

    for item in cart:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
            (order_id, item["product_id"], item["quantity"], item["price"]),
        )

    conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Order created", "order_id": order_id}


def process_payment_callback(order_id: int, payment_status: str, transaction_id: str) -> dict:
    conn = get_connection()
    order = conn.execute(
        "SELECT id, user_id, status, payment_txn_id FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    if order is None:
        conn.close()
        return {"success": False, "message": "Order not found", "error_code": "ORDER_NOT_FOUND"}

    if order["payment_txn_id"] == transaction_id:
        conn.close()
        return {"success": False, "message": "Duplicate payment callback", "error_code": "DUPLICATE_PAYMENT"}

    if order["status"] == "paid":
        conn.close()
        return {"success": False, "message": "Order already paid", "error_code": "ALREADY_PAID"}

    if order["status"] == "cancelled":
        conn.close()
        return {"success": False, "message": "Order cancelled", "error_code": "ORDER_CANCELLED"}

    if payment_status == "failed":
        conn.execute("UPDATE orders SET status = 'payment_failed' WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()
        return {"success": True, "message": "Payment failed recorded", "order_id": order_id, "status": "payment_failed"}

    items = conn.execute(
        "SELECT oi.product_id, oi.quantity, p.stock, p.name FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?",
        (order_id,),
    ).fetchall()
    for item in items:
        if item["quantity"] > item["stock"]:
            conn.close()
            return {"success": False, "message": f"Insufficient stock for {item['name']}", "error_code": "INSUFFICIENT_STOCK"}

    for item in items:
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (item["quantity"], item["product_id"]),
        )

    conn.execute(
        "UPDATE orders SET status = 'paid', payment_txn_id = ? WHERE id = ?",
        (transaction_id, order_id),
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": "Payment success", "order_id": order_id, "status": "paid"}


def cancel_order(user_id: int, order_id: int) -> dict:
    conn = get_connection()
    order = conn.execute(
        "SELECT id, user_id, status FROM orders WHERE id = ? AND user_id = ?",
        (order_id, user_id),
    ).fetchone()
    if order is None:
        conn.close()
        return {"success": False, "message": "Order not found", "error_code": "ORDER_NOT_FOUND"}

    if order["status"] == "cancelled":
        conn.close()
        return {"success": False, "message": "Order already cancelled", "error_code": "ALREADY_CANCELLED"}

    if order["status"] == "paid":
        items = conn.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()
        for item in items:
            conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )

    conn.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Order cancelled", "order_id": order_id, "status": "cancelled"}


def get_orders(user_id: int, order_id: int | None = None) -> list[dict]:
    conn = get_connection()
    if order_id is not None:
        orders = conn.execute(
            "SELECT id, user_id, total_amount, discount_amount, status, created_at, payment_txn_id FROM orders WHERE user_id = ? AND id = ?",
            (user_id, order_id),
        ).fetchall()
    else:
        orders = conn.execute(
            "SELECT id, user_id, total_amount, discount_amount, status, created_at, payment_txn_id FROM orders WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()

    result = []
    for order in orders:
        items = conn.execute(
            """
            SELECT oi.product_id, p.name AS product_name, oi.quantity, oi.unit_price
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
            """,
            (order["id"],),
        ).fetchall()
        order_dict = dict(order)
        order_dict["items"] = [dict(i) for i in items]
        result.append(order_dict)

    conn.close()
    return result
