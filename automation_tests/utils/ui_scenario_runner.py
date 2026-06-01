"""Run Playwright UI scenarios defined in JSON data files."""

from playwright.sync_api import Page, expect

from ui.conftest import wait_for_orders_loaded, wait_for_products_loaded


def _login(page: Page, base_url: str, username: str, password: str) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded", timeout=60000)
    expect(page.get_by_test_id("login-title")).to_be_visible(timeout=30000)
    expect(page.get_by_test_id("username-input")).to_be_visible(timeout=30000)
    page.get_by_test_id("username-input").fill(username)
    page.get_by_test_id("password-input").fill(password)
    page.get_by_test_id("login-submit-btn").click()


def run_ui_actions(page: Page, base_url: str, actions: list[dict]) -> None:
    for action in actions:
        kind = action["type"]
        if kind == "fill":
            page.get_by_test_id(action["test_id"]).fill(action["value"])
        elif kind == "click":
            page.get_by_test_id(action["test_id"]).click()
        elif kind == "select":
            page.get_by_test_id(action["test_id"]).select_option(action["value"])
        elif kind == "wait_products":
            wait_for_products_loaded(page)
        elif kind == "wait_url_contains":
            page.wait_for_url(f"**{action['value']}**", timeout=action.get("timeout", 10000))
        elif kind == "expect_visible":
            expect(page.get_by_test_id(action["test_id"])).to_be_visible()
        elif kind == "sleep_ms":
            page.wait_for_timeout(action["value"])
        else:
            raise ValueError(f"Unknown UI action: {kind}")


def execute_ui_case(page: Page, base_url: str, case: dict) -> None:
    case_id = case["case_id"]
    flow = case.get("flow")

    if flow == "login":
        page.goto(f"{base_url}/login", wait_until="domcontentloaded", timeout=60000)
        expect(page.get_by_test_id("login-title")).to_be_visible(timeout=30000)
        if case_id == "login_success":
            expect(page.get_by_test_id("login-title")).to_be_visible()
        expect(page.get_by_test_id("username-input")).to_be_visible(timeout=30000)
        page.get_by_test_id("username-input").fill(case["username"])
        page.get_by_test_id("password-input").fill(case["password"])
        page.get_by_test_id("login-submit-btn").click()
        if url_part := case.get("expect_url_contains"):
            page.wait_for_url(f"**{url_part}**")
        elif case_id == "login_failure":
            expect(page.get_by_test_id("login-error")).to_be_visible(timeout=10000)
        for test_id in case.get("expect_visible", []):
            expect(page.get_by_test_id(test_id)).to_be_visible()
        for test_id, text in case.get("expect_text", {}).items():
            expect(page.get_by_test_id(test_id)).to_contain_text(text)
        return

    if flow == "redirect":
        page.goto(f"{base_url}{case['goto_path']}")
        if url_part := case.get("expect_url_contains"):
            page.wait_for_url(f"**{url_part}**")
        return

    if login := case.get("login"):
        _login(page, base_url, login["username"], login["password"])
        page.wait_for_url(f"{base_url}/products")
    elif case.get("requires_login"):
        _login(page, base_url, "alice", "password123")
        page.wait_for_url(f"{base_url}/products")

    if actions := case.get("actions"):
        run_ui_actions(page, base_url, actions)

    for test_id in case.get("expect_visible", []):
        expect(page.get_by_test_id(test_id)).to_be_visible()

    for test_id, text in case.get("expect_text", {}).items():
        expect(page.get_by_test_id(test_id)).to_contain_text(text)

    if count_rule := case.get("expect_count"):
        expect(page.locator(count_rule["selector"])).to_have_count(count_rule["equals"])

    if min_rule := case.get("expect_min_count"):
        assert page.locator(min_rule["selector"]).count() >= min_rule["min"], case_id

    if case.get("expect_badge_not"):
        expect(page.get_by_test_id("cart-badge")).not_to_have_text(case["expect_badge_not"])

    if case.get("expect_first_order_status"):
        wait_for_orders_loaded(page)
        cards = page.locator("[data-testid^='order-card-']")
        expect(cards.first).to_be_visible(timeout=15000)
        expect(cards.first.locator("[data-testid^='order-status-']")).to_contain_text(
            case["expect_first_order_status"],
            timeout=10000,
        )
