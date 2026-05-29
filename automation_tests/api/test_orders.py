"""Order, payment, cancel, cart merge, inventory and DB assertion tests."""

import uuid

import allure
import pytest

from utils.schema_validator import validate_json

pytestmark = [pytest.mark.api, pytest.mark.order]


def _add_cart(client, product_id: int, quantity: int = 1):
    return client.post("/api/cart/items", json={"product_id": product_id, "quantity": quantity})


def _create_order(client):
    return client.post("/api/orders")


@pytest.fixture
def pay_callback(base_url):
    def _pay(order_id: int, txn: str | None = None, status: str = "success"):
        import requests
        txn = txn or f"txn_{uuid.uuid4().hex[:12]}"
        return requests.post(
            f"{base_url}/api/payments/callback",
            json={"order_id": order_id, "payment_status": status, "transaction_id": txn},
            timeout=5,
        )
    return _pay


@pytest.fixture
def pending_order(auth_client):
    _add_cart(auth_client, 8, 1)
    resp = _create_order(auth_client)
    assert resp.status_code == 200
    return resp.json()["order"]


@pytest.fixture
def paid_order(auth_client, pay_callback, pending_order):
    oid = pending_order["id"]
    pay_callback(oid)
    resp = auth_client.get(f"/api/orders/{oid}")
    return resp.json()


class TestOrderFlow:
    @allure.title("创建订单后状态为 pending")
    def test_create_order_pending(self, pending_order, db_helper):
        assert pending_order["status"] == "pending"
        db_row = db_helper.get_order(pending_order["id"])
        assert db_row["status"] == "pending"

    @allure.title("支付回调成功后订单变为 paid 且扣减库存")
    def test_payment_callback_success(self, auth_client, pay_callback, pending_order, db_helper):
        oid = pending_order["id"]
        stock_before = db_helper.get_product_stock(8)
        resp = pay_callback(oid)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"
        assert db_helper.get_order(oid)["status"] == "paid"
        assert db_helper.get_product_stock(8) == stock_before - 1

    @allure.title("重复支付回调被拒绝")
    def test_duplicate_payment_callback(self, pay_callback, pending_order):
        oid = pending_order["id"]
        txn = f"txn_dup_{uuid.uuid4().hex[:8]}"
        assert pay_callback(oid, txn).status_code == 200
        resp = pay_callback(oid, txn)
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "DUPLICATE_PAYMENT"

    @allure.title("取消 pending 订单")
    def test_cancel_pending_order(self, auth_client, pending_order, db_helper):
        oid = pending_order["id"]
        resp = auth_client.post(f"/api/orders/{oid}/cancel")
        assert resp.status_code == 200
        assert db_helper.get_order(oid)["status"] == "cancelled"

    @allure.title("订单 JSON Schema 校验")
    def test_order_json_schema(self, paid_order):
        errors = validate_json(paid_order, "order_response.json")
        assert errors == [], errors

    @allure.title("优惠金额与总价计算")
    def test_discount_calculation(self, auth_client, db_helper):
        _add_cart(auth_client, 1, 1)
        order = _create_order(auth_client).json()["order"]
        subtotal = 7999.0
        expected_discount = round(subtotal * 0.1, 2)
        assert order["discount_amount"] == expected_discount
        assert order["total_amount"] == round(subtotal - expected_discount, 2)


class TestOrderQuery:
    def test_list_orders(self, auth_client, paid_order):
        resp = auth_client.get("/api/orders")
        assert resp.status_code == 200
        assert any(o["id"] == paid_order["id"] for o in resp.json())

    def test_get_order_by_id(self, auth_client, paid_order):
        resp = auth_client.get(f"/api/orders/{paid_order['id']}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"

    @pytest.mark.parametrize("oid,code", [(0, "INVALID_ORDER_ID"), (99999, "ORDER_NOT_FOUND")])
    def test_invalid_order_id(self, auth_client, oid, code):
        resp = auth_client.get(f"/api/orders/{oid}")
        assert resp.status_code in (400, 404)
        assert resp.json()["detail"]["error_code"] == code


class TestCartAndInventory:
    @pytest.mark.parametrize("quantity,expected_status", [(0, 422), (-1, 422)])
    def test_add_cart_invalid_quantity(self, auth_client, quantity, expected_status):
        resp = _add_cart(auth_client, 1, quantity)
        assert resp.status_code == expected_status

    def test_cart_merge_same_product(self, auth_client, db_helper):
        _add_cart(auth_client, 8, 1)
        _add_cart(auth_client, 8, 2)
        resp = auth_client.get("/api/cart")
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["quantity"] == 3

    def test_insufficient_stock_on_order(self, auth_client, db_helper):
        original = db_helper.get_product_stock(8)
        try:
            db_helper.set_product_stock(8, 1)
            _add_cart(auth_client, 8, 5)
            resp = _create_order(auth_client)
            assert resp.status_code == 400
            assert resp.json()["error_code"] == "INSUFFICIENT_STOCK"
        finally:
            db_helper.set_product_stock(8, original)

    def test_duplicate_submit_empty_cart(self, auth_client):
        _add_cart(auth_client, 7, 1)
        assert _create_order(auth_client).status_code == 200
        resp = _create_order(auth_client)
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "EMPTY_CART"

    def test_create_order_empty_cart_bob(self, api_client):
        token = api_client.login("bob", "password456")
        client = api_client.with_token(token)
        resp = client.post("/api/orders")
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "EMPTY_CART"

    @pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer bad"}], ids=["no_token", "bad_token"])
    def test_order_auth_required(self, api_client, headers):
        resp = api_client.get("/api/orders", headers=headers)
        assert resp.status_code == 401
