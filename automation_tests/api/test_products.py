"""Product search & filter API parameterized tests."""

import pytest
import requests

from utils.data_loader import load_test_cases
from utils.product_assertions import run_product_assertions
from utils.schema_validator import validate_json

pytestmark = pytest.mark.api

PRODUCT_CASES = load_test_cases("product_cases.json")


class TestProductSearchAPI:
    @pytest.mark.parametrize(
        "case",
        PRODUCT_CASES,
        ids=[c["case_id"] for c in PRODUCT_CASES],
    )
    def test_product_search(self, base_url, case):
        case_id = case["case_id"]
        params = case["params"]
        expected_status = case["expected_status"]
        assertions = case.get("assertions")

        resp = requests.get(f"{base_url}/api/products", params=params)
        assert resp.status_code == expected_status, f"[{case_id}] unexpected status"

        if expected_status == 200:
            data = resp.json()
            assert isinstance(data, list)
            schema_errors = validate_json(data, "product_list.json")
            assert schema_errors == [], schema_errors
            run_product_assertions(data, assertions, case_id)
            if data:
                product = data[0]
                assert set(product.keys()) >= {"id", "name", "category", "price", "stock", "description"}
                assert isinstance(product["price"], (int, float))
                assert product["price"] >= 0
        elif expected_status == 400:
            detail = resp.json()["detail"]
            assert detail["error_code"] == "INVALID_PRICE_RANGE"

    def test_product_response_types(self, base_url):
        resp = requests.get(f"{base_url}/api/products")
        products = resp.json()
        assert len(products) > 0
        p = products[0]
        assert isinstance(p["id"], int)
        assert isinstance(p["name"], str)
        assert isinstance(p["stock"], int)
        assert p["stock"] >= 0
