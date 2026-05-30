"""Login API parameterized tests — covers normal, abnormal, and boundary cases."""

import pytest
import requests

from utils.data_loader import load_test_cases
from utils.schema_validator import validate_json

pytestmark = pytest.mark.api

LOGIN_CASES = load_test_cases("login_cases.json")


class TestLoginAPI:
    @pytest.mark.parametrize(
        "case",
        LOGIN_CASES,
        ids=[c["case_id"] for c in LOGIN_CASES],
    )
    def test_login(self, base_url, case):
        case_id = case["case_id"]
        payload = case["payload"]
        expected_status = case["expected_status"]
        expect_success = case["expect_success"]
        msg_fragment = case.get("msg_fragment")

        resp = requests.post(f"{base_url}/api/auth/login", json=payload)
        assert resp.status_code == expected_status, f"[{case_id}] unexpected status"

        if expect_success:
            data = resp.json()
            assert data["success"] is True
            assert data["token"] is not None
            assert data["user_id"] is not None
            assert data["username"] is not None
            if msg_fragment:
                assert msg_fragment in data["message"]
        elif expected_status in (401, 400):
            data = resp.json()
            assert data["success"] is False
            if msg_fragment:
                assert msg_fragment in data["message"]

    def test_login_response_fields(self, base_url):
        resp = requests.post(
            f"{base_url}/api/auth/login",
            json={"username": "alice", "password": "password123"},
        )
        data = resp.json()
        errors = validate_json(data, "login_response.json")
        assert errors == [], errors
        assert isinstance(data["token"], str) and len(data["token"]) > 0
