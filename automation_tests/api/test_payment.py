"""Payment callback API tests."""

import allure
import pytest

from utils.api_scenario_runner import execute_api_case
from utils.data_loader import load_test_cases

pytestmark = [pytest.mark.api, pytest.mark.payment]

PAYMENT_CASES = load_test_cases("payment_cases.json")


@allure.feature("支付回调")
class TestPaymentAPI:
    @pytest.mark.parametrize("case", PAYMENT_CASES, ids=[c["case_id"] for c in PAYMENT_CASES])
    def test_payment_scenarios(self, base_url, auth_client, db_helper, case):
        allure.dynamic.title(case["case_id"])
        execute_api_case(case, auth_client, auth_client, base_url, db_helper)
