"""Payment callback API tests."""

import uuid

import allure
import pytest

pytestmark = [pytest.mark.api, pytest.mark.payment]


@allure.feature("支付回调")
class TestPaymentAPI:
    def test_payment_failed_status(self, base_url, auth_client):
        auth_client.post("/api/cart/items", json={"product_id": 8, "quantity": 1})
        order = auth_client.post("/api/orders").json()["order"]
        import requests
        resp = requests.post(
            f"{base_url}/api/payments/callback",
            json={
                "order_id": order["id"],
                "payment_status": "failed",
                "transaction_id": f"txn_fail_{uuid.uuid4().hex[:8]}",
            },
            timeout=5,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "payment_failed"

    def test_payment_on_cancelled_order(self, base_url, auth_client):
        auth_client.post("/api/cart/items", json={"product_id": 8, "quantity": 1})
        order = auth_client.post("/api/orders").json()["order"]
        auth_client.post(f"/api/orders/{order['id']}/cancel")
        import requests
        resp = requests.post(
            f"{base_url}/api/payments/callback",
            json={
                "order_id": order["id"],
                "payment_status": "success",
                "transaction_id": f"txn_{uuid.uuid4().hex[:8]}",
            },
            timeout=5,
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "ORDER_CANCELLED"
