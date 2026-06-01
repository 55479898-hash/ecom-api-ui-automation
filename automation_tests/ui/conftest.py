"""Playwright UI conftest — page fixtures, test data management, stable locators."""

import os
import uuid

import pytest
from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("ECOM_BASE_URL", "http://127.0.0.1:8000")
ALICE_USER_ID = 1


@pytest.fixture
def unique_user():
    """Generate unique test credentials to avoid duplicate data conflicts."""
    suffix = uuid.uuid4().hex[:8]
    return {
        "username": f"ui_test_{suffix}",
        "password": "uitest1234",
    }


@pytest.fixture
def logged_in_page(page: Page, base_url):
    """Pre-authenticated page using the shared test account."""
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.get_by_test_id("username-input").wait_for(state="visible", timeout=15000)
    page.get_by_test_id("username-input").fill("alice")
    page.get_by_test_id("password-input").fill("password123")
    page.get_by_test_id("login-submit-btn").click()
    page.wait_for_url(f"{base_url}/products")
    expect(page.get_by_test_id("products-title")).to_be_visible()
    return page


def wait_for_products_loaded(page: Page):
    """Wait for product list to finish loading (handles async fetch)."""
    page.wait_for_selector("[data-testid='product-list']", state="attached")
    page.wait_for_function(
        """() => {
            const count = document.getElementById('product-count');
            return count && count.textContent.includes('共');
        }""",
        timeout=10000,
    )


def wait_for_orders_loaded(page: Page):
    """Wait for order list API render to finish."""
    page.wait_for_selector("[data-testid='order-list']", state="attached")
    page.wait_for_function(
        """() => {
            const list = document.getElementById('order-list');
            const empty = document.getElementById('no-orders');
            if (!list) return false;
            if (list.children.length > 0) return true;
            return empty && !empty.classList.contains('hidden');
        }""",
        timeout=15000,
    )


@pytest.fixture(autouse=True)
def isolate_alice_cart(db_helper):
    """Avoid cart pollution when multiple UI cases reuse alice."""
    db_helper.clear_cart(ALICE_USER_ID)
    yield
    db_helper.clear_cart(ALICE_USER_ID)
