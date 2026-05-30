"""Execute API test scenarios defined in JSON data files."""

from __future__ import annotations

import uuid
from typing import Any

import requests


class ScenarioContext:
    def __init__(self):
        self.data: dict[str, Any] = {}


def _resolve_ref(value: Any, ctx: ScenarioContext) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        return ctx.data[value[1:]]
    return value


def run_api_steps(
    client,
    steps: list[dict],
    ctx: ScenarioContext,
    *,
    base_url: str | None = None,
    db_helper=None,
) -> requests.Response | None:
    last_resp = None
    for step in steps:
        action = step["action"]
        if action == "add_cart":
            last_resp = client.post(
                "/api/cart/items",
                json={"product_id": step["product_id"], "quantity": step["quantity"]},
            )
        elif action == "create_order":
            last_resp = client.post("/api/orders")
            if last_resp.status_code == 200:
                ctx.data[step.get("save_as", "order")] = last_resp.json()["order"]
        elif action == "cancel_order":
            order = _resolve_ref(step.get("order_ref", "$order"), ctx)
            last_resp = client.post(f"/api/orders/{order['id']}/cancel")
        elif action == "get_cart":
            last_resp = client.get("/api/cart")
            if last_resp.status_code == 200:
                ctx.data["cart"] = last_resp.json()
        elif action == "set_stock":
            assert db_helper is not None
            product_id = step["product_id"]
            original = db_helper.get_product_stock(product_id)
            ctx.data.setdefault("_restore_stock", []).append((product_id, original))
            db_helper.set_product_stock(product_id, step["stock"])
        elif action == "pay_callback":
            assert base_url is not None
            order = _resolve_ref(step.get("order_ref", "$order"), ctx)
            txn = step.get("transaction_id")
            if isinstance(txn, str) and txn.startswith("$"):
                txn = ctx.data[txn[1:]]
            if not txn:
                txn = f"txn_{uuid.uuid4().hex[:12]}"
            last_resp = requests.post(
                f"{base_url}/api/payments/callback",
                json={
                    "order_id": order["id"],
                    "payment_status": step.get("payment_status", "success"),
                    "transaction_id": txn,
                },
                timeout=5,
            )
            if step.get("save_txn"):
                ctx.data["transaction_id"] = txn
        elif action == "login_as":
            token = client.login(step["username"], step["password"])
            ctx.data["client"] = client.with_token(token)
        else:
            raise ValueError(f"Unknown action: {action}")
    return last_resp


def restore_stock(db_helper, ctx: ScenarioContext) -> None:
    for product_id, stock in ctx.data.get("_restore_stock", []):
        db_helper.set_product_stock(product_id, stock)


def snapshot_stock(db_helper, ctx: ScenarioContext, product_id: int) -> None:
    ctx.data[f"_stock_before_{product_id}"] = db_helper.get_product_stock(product_id)


def record_stock_delta(db_helper, ctx: ScenarioContext, product_id: int) -> None:
    before = ctx.data.get(f"_stock_before_{product_id}")
    after = db_helper.get_product_stock(product_id)
    if before is not None:
        ctx.data[f"_stock_delta_{product_id}"] = after - before


def run_order_assertions(case: dict, ctx: ScenarioContext, db_helper, last_resp) -> None:
    case_id = case["case_id"]
    for rule in case.get("assertions", []):
        kind = rule["type"]
        if kind == "response_status":
            assert last_resp.status_code == rule["equals"], f"[{case_id}] status"
        elif kind == "response_error_code":
            assert last_resp.json()["error_code"] == rule["equals"], f"[{case_id}] error_code"
        elif kind == "response_json_field":
            body = ctx.data["order"] if rule.get("on") == "order" else last_resp.json()
            assert body[rule["field"]] == rule["equals"], f"[{case_id}] {rule['field']}"
        elif kind == "order_status":
            order = _resolve_ref(rule.get("order_ref", "$order"), ctx)
            row = db_helper.get_order(order["id"])
            assert row["status"] == rule["equals"], f"[{case_id}] db order status"
        elif kind == "stock_delta":
            product_id = rule["product_id"]
            expected = rule["delta"]
            actual_delta = ctx.data.get(f"_stock_delta_{product_id}")
            assert actual_delta == expected, f"[{case_id}] stock delta"
        elif kind == "cart_items_count":
            cart = ctx.data["cart"]
            assert len(cart["items"]) == rule["equals"], f"[{case_id}] cart count"
        elif kind == "cart_item_quantity":
            cart = ctx.data["cart"]
            item = next(i for i in cart["items"] if i["product_id"] == rule["product_id"])
            assert item["quantity"] == rule["equals"], f"[{case_id}] cart qty"
        elif kind == "order_discount":
            order = ctx.data["order"]
            subtotal = rule["subtotal"]
            rate = rule["rate"]
            expected_discount = round(subtotal * rate, 2)
            assert order["discount_amount"] == expected_discount, f"[{case_id}] discount"
            assert order["total_amount"] == round(subtotal - expected_discount, 2), f"[{case_id}] total"
        else:
            raise ValueError(f"Unknown assertion: {kind}")


def execute_api_case(case, auth_client, api_client, base_url, db_helper):
    ctx = ScenarioContext()
    client = auth_client
    if login := case.get("use_login"):
        run_api_steps(api_client, [{"action": "login_as", **login}], ctx)
        client = ctx.data["client"]

    product_id = case.get("snapshot_stock")
    if product_id is not None:
        snapshot_stock(db_helper, ctx, product_id)

    try:
        last_resp = run_api_steps(
            client,
            case.get("steps", []),
            ctx,
            base_url=base_url,
            db_helper=db_helper,
        )

        if product_id is not None:
            record_stock_delta(db_helper, ctx, product_id)

        if "expected_status" in case:
            assert last_resp.status_code == case["expected_status"], case["case_id"]
            if code := case.get("expected_error_code"):
                assert last_resp.json()["error_code"] == code, case["case_id"]

        if status := case.get("expected_order_status"):
            order = ctx.data["order"]
            row = db_helper.get_order(order["id"])
            assert row["status"] == status, case["case_id"]

        run_order_assertions(case, ctx, db_helper, last_resp)
        return last_resp, ctx
    finally:
        if case.get("restore_stock"):
            restore_stock(db_helper, ctx)
