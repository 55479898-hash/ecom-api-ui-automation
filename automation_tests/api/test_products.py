"""Product search & filter API parameterized tests."""

import pytest
import requests

pytestmark = pytest.mark.api


PRODUCT_CASES = [
    ("all_products", {}, 200, lambda r: len(r) == 10),
    ("search_iphone", {"q": "iPhone"}, 200, lambda r: len(r) >= 1 and any("iPhone" in p["name"] for p in r)),
    ("search_book", {"q": "Python"}, 200, lambda r: len(r) >= 1),
    ("search_no_result", {"q": "zzzznotexist"}, 200, lambda r: len(r) == 0),
    ("filter_electronics", {"category": "electronics"}, 200, lambda r: all(p["category"] == "electronics" for p in r)),
    ("filter_clothing", {"category": "clothing"}, 200, lambda r: all(p["category"] == "clothing" for p in r)),
    ("filter_books", {"category": "books"}, 200, lambda r: all(p["category"] == "books" for p in r)),
    ("filter_home", {"category": "home"}, 200, lambda r: all(p["category"] == "home" for p in r)),
    ("price_min_500", {"min_price": 500}, 200, lambda r: all(p["price"] >= 500 for p in r)),
    ("price_max_100", {"max_price": 100}, 200, lambda r: all(p["price"] <= 100 for p in r)),
    ("price_range", {"min_price": 100, "max_price": 1000}, 200, lambda r: all(100 <= p["price"] <= 1000 for p in r)),
    ("combined_search", {"q": "Air", "category": "electronics"}, 200, lambda r: all(p["category"] == "electronics" for p in r)),
    ("invalid_price_range", {"min_price": 1000, "max_price": 100}, 400, None),
    ("negative_min_price", {"min_price": -1}, 422, None),
    ("zero_max_price", {"max_price": 0}, 200, lambda r: all(p["price"] <= 0 for p in r)),
    ("empty_query", {"q": ""}, 200, lambda r: len(r) == 10),
    ("special_char_query", {"q": "%_"}, 200, lambda r: isinstance(r, list)),
    ("uppercase_category", {"category": "ELECTRONICS"}, 200, lambda r: all(p["category"] == "electronics" for p in r)),
]


class TestProductSearchAPI:
    @pytest.mark.parametrize(
        "case_id,params,expected_status,validator",
        PRODUCT_CASES,
        ids=[c[0] for c in PRODUCT_CASES],
    )
    def test_product_search(self, base_url, case_id, params, expected_status, validator):
        resp = requests.get(f"{base_url}/api/products", params=params)
        assert resp.status_code == expected_status, f"[{case_id}] unexpected status"

        if expected_status == 200:
            data = resp.json()
            assert isinstance(data, list)
            from utils.schema_validator import validate_json
            schema_errors = validate_json(data, "product_list.json")
            assert schema_errors == [], schema_errors
            if validator:
                assert validator(data), f"[{case_id}] validation failed"
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
