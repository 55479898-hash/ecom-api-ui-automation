"""Playwright E2E tests driven by JSON scenario data."""

import pytest
from playwright.sync_api import Page

from utils.data_loader import load_test_cases
from utils.ui_scenario_runner import execute_ui_case

pytestmark = pytest.mark.ui

UI_LOGIN_CASES = load_test_cases("ui_login_cases.json")
UI_PRODUCT_CASES = load_test_cases("ui_product_cases.json")
UI_CART_CASES = load_test_cases("ui_cart_cases.json")


class TestLoginFlow:
    @pytest.mark.parametrize("case", UI_LOGIN_CASES, ids=[c["case_id"] for c in UI_LOGIN_CASES])
    def test_login_flow(self, page: Page, base_url, case):
        execute_ui_case(page, base_url, case)


class TestProductFilterFlow:
    @pytest.mark.parametrize("case", UI_PRODUCT_CASES, ids=[c["case_id"] for c in UI_PRODUCT_CASES])
    def test_product_filter_flow(self, page: Page, base_url, case):
        execute_ui_case(page, base_url, case)


class TestCartAndOrderFlow:
    @pytest.mark.parametrize("case", UI_CART_CASES, ids=[c["case_id"] for c in UI_CART_CASES])
    def test_cart_and_order_flow(self, page: Page, base_url, case):
        execute_ui_case(page, base_url, case)
