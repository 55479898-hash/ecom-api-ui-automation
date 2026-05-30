"""Order, payment, cancel, cart merge, inventory and DB assertion tests."""

import allure
import pytest

from utils.api_scenario_runner import execute_api_case
from utils.data_loader import load_test_cases
from utils.schema_validator import validate_json

pytestmark = [pytest.mark.api, pytest.mark.order]

ORDER_FLOW_CASES = load_test_cases("order_flow_cases.json")
ORDER_SCENARIO_CASES = load_test_cases("order_scenarios.json")
ORDER_QUERY_CASES = load_test_cases("order_query_cases.json")
ORDER_AUTH_CASES = load_test_cases("order_auth_cases.json")


@pytest.fixture
def paid_order(auth_client, base_url, db_helper):
    case = next(c for c in ORDER_FLOW_CASES if c["case_id"] == "payment_callback_success")
    _, ctx = execute_api_case(case, auth_client, auth_client, base_url, db_helper)
    return ctx.data["order"]


class TestOrderFlow:
    @pytest.mark.parametrize("case", ORDER_FLOW_CASES, ids=[c["case_id"] for c in ORDER_FLOW_CASES])
    def test_order_flow(self, auth_client, base_url, db_helper, case):
        allure.dynamic.title(case["case_id"])
        execute_api_case(case, auth_client, auth_client, base_url, db_helper)

    @allure.title("订单 JSON Schema 校验")
    def test_order_json_schema(self, paid_order):
        errors = validate_json(paid_order, "order_response.json")
        assert errors == [], errors


class TestOrderQuery:
    def test_list_orders(self, auth_client, paid_order):
        resp = auth_client.get("/api/orders")
        assert resp.status_code == 200
        assert any(o["id"] == paid_order["id"] for o in resp.json())

    def test_get_order_by_id(self, auth_client, paid_order):
        resp = auth_client.get(f"/api/orders/{paid_order['id']}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"

    @pytest.mark.parametrize("case", ORDER_QUERY_CASES, ids=[c["case_id"] for c in ORDER_QUERY_CASES])
    def test_invalid_order_id(self, auth_client, case):
        resp = auth_client.get(f"/api/orders/{case['order_id']}")
        assert resp.status_code in case["expected_statuses"]
        assert resp.json()["detail"]["error_code"] == case["expected_error_code"]


class TestCartAndInventory:
    @pytest.mark.parametrize("case", ORDER_SCENARIO_CASES, ids=[c["case_id"] for c in ORDER_SCENARIO_CASES])
    def test_order_scenarios(self, auth_client, api_client, base_url, db_helper, case):
        allure.dynamic.title(case["case_id"])
        execute_api_case(case, auth_client, api_client, base_url, db_helper)

    @pytest.mark.parametrize("case", ORDER_AUTH_CASES, ids=[c["case_id"] for c in ORDER_AUTH_CASES])
    def test_order_auth_required(self, api_client, case):
        resp = api_client.get("/api/orders", headers=case["headers"])
        assert resp.status_code == case["expected_status"]
