"""Playwright UI conftest — page fixtures, test data management, stable locators."""

import os
import uuid

import pytest
from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("ECOM_BASE_URL", "http://127.0.0.1:8000")


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
    page.goto(f"{base_url}/login")
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
