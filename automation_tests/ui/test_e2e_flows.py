"""Playwright E2E tests: Login, Product Filter, Add to Cart, Place Order."""

import pytest
from playwright.sync_api import Page, expect

from ui.conftest import BASE_URL, wait_for_products_loaded

pytestmark = pytest.mark.ui


class TestLoginFlow:
    def test_login_success(self, page: Page, base_url):
        page.goto(f"{base_url}/login")
        expect(page.get_by_test_id("login-title")).to_be_visible()

        page.get_by_test_id("username-input").fill("alice")
        page.get_by_test_id("password-input").fill("password123")
        page.get_by_test_id("login-submit-btn").click()

        page.wait_for_url(f"{base_url}/products")
        expect(page.get_by_test_id("products-title")).to_be_visible()
        expect(page.get_by_test_id("user-info")).to_contain_text("alice")

    def test_login_failure_shows_error(self, page: Page, base_url):
        page.goto(f"{base_url}/login")
        page.get_by_test_id("username-input").fill("alice")
        page.get_by_test_id("password-input").fill("wrongpassword")
        page.get_by_test_id("login-submit-btn").click()

        error = page.get_by_test_id("login-error")
        expect(error).to_be_visible()
        expect(error).to_contain_text("Invalid username or password")

    def test_unauthenticated_redirect_to_login(self, page: Page, base_url):
        page.goto(f"{base_url}/cart")
        page.wait_for_url(f"{base_url}/login")


class TestProductFilterFlow:
    def test_search_by_keyword(self, logged_in_page: Page, base_url):
        page = logged_in_page
        page.get_by_test_id("search-input").fill("iPhone")
        page.get_by_test_id("filter-btn").click()
        wait_for_products_loaded(page)

        expect(page.get_by_test_id("product-count")).to_contain_text("共 1 件商品")
        expect(page.get_by_test_id("product-name-1")).to_contain_text("iPhone")

    def test_filter_by_category(self, logged_in_page: Page, base_url):
        page = logged_in_page
        page.get_by_test_id("category-filter").select_option("books")
        page.get_by_test_id("filter-btn").click()
        wait_for_products_loaded(page)

        cards = page.locator("[data-testid^='product-card-']")
        expect(cards).to_have_count(2)
        expect(page.get_by_test_id("product-category-7")).to_contain_text("books")

    def test_filter_by_price_range(self, logged_in_page: Page, base_url):
        page = logged_in_page
        page.get_by_test_id("min-price-input").fill("500")
        page.get_by_test_id("max-price-input").fill("2000")
        page.get_by_test_id("filter-btn").click()
        wait_for_products_loaded(page)

        count_text = page.get_by_test_id("product-count").inner_text()
        assert "共" in count_text
        cards = page.locator("[data-testid^='product-card-']")
        assert cards.count() >= 1

    def test_reset_filters(self, logged_in_page: Page, base_url):
        page = logged_in_page
        page.get_by_test_id("search-input").fill("nonexistent")
        page.get_by_test_id("filter-btn").click()
        wait_for_products_loaded(page)
        expect(page.get_by_test_id("no-products-msg")).to_be_visible()

        page.get_by_test_id("reset-filter-btn").click()
        wait_for_products_loaded(page)
        expect(page.get_by_test_id("product-count")).to_contain_text("共 10 件商品")


class TestCartAndOrderFlow:
    def test_add_to_cart_and_checkout(self, logged_in_page: Page, base_url):
        page = logged_in_page

        page.get_by_test_id("search-input").fill("Python")
        page.get_by_test_id("filter-btn").click()
        wait_for_products_loaded(page)

        page.get_by_test_id("add-cart-btn-7").click()
        expect(page.get_by_test_id("toast")).to_be_visible()

        page.get_by_test_id("nav-cart").click()
        page.wait_for_url(f"{base_url}/cart")
        expect(page.get_by_test_id("cart-item-7")).to_be_visible()

        page.get_by_test_id("checkout-btn").click()
        page.wait_for_url(f"{base_url}/orders", timeout=15000)
        expect(page.get_by_test_id("orders-title")).to_be_visible()

        order_cards = page.locator("[data-testid^='order-card-']")
        expect(order_cards.first).to_be_visible()
        expect(order_cards.first.locator("[data-testid^='order-status-']")).to_contain_text("paid")

    def test_cart_badge_updates(self, logged_in_page: Page, base_url):
        page = logged_in_page
        page.get_by_test_id("add-cart-btn-3").click()
        page.wait_for_timeout(500)
        badge = page.get_by_test_id("cart-badge")
        expect(badge).not_to_have_text("0")

    def test_empty_cart_message(self, page: Page, base_url):
        """Use bob who has empty cart."""
        page.goto(f"{base_url}/login")
        page.get_by_test_id("username-input").fill("bob")
        page.get_by_test_id("password-input").fill("password456")
        page.get_by_test_id("login-submit-btn").click()
        page.wait_for_url(f"{base_url}/products")

        page.get_by_test_id("nav-cart").click()
        page.wait_for_url(f"{base_url}/cart")
        expect(page.get_by_test_id("empty-cart-msg")).to_be_visible()
