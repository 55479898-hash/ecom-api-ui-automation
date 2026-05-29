"""Login API parameterized tests — covers normal, abnormal, and boundary cases."""

import pytest
import requests

pytestmark = pytest.mark.api


LOGIN_CASES = [
    # (case_id, payload, expected_status, expect_success, expected_msg_fragment)
    ("valid_alice", {"username": "alice", "password": "password123"}, 200, True, "Login successful"),
    ("valid_bob", {"username": "bob", "password": "password456"}, 200, True, "Login successful"),
    ("valid_testuser", {"username": "testuser", "password": "test1234"}, 200, True, "Login successful"),
    ("wrong_password", {"username": "alice", "password": "wrongpass"}, 401, False, "Invalid username or password"),
    ("wrong_username", {"username": "nonexistent", "password": "password123"}, 401, False, "Invalid username or password"),
    ("empty_username", {"username": "", "password": "password123"}, 422, False, None),
    ("empty_password", {"username": "alice", "password": ""}, 422, False, None),
    ("both_empty", {"username": "", "password": ""}, 422, False, None),
    ("username_with_spaces", {"username": "  alice  ", "password": "password123"}, 200, True, "Login successful"),
    ("case_sensitive_password", {"username": "alice", "password": "Password123"}, 401, False, "Invalid username or password"),
    ("sql_injection_username", {"username": "admin' OR '1'='1", "password": "x"}, 401, False, "Invalid username or password"),
    ("xss_username", {"username": "<script>alert(1)</script>", "password": "x"}, 401, False, "Invalid username or password"),
    ("very_long_username", {"username": "a" * 256, "password": "password123"}, 401, False, "Invalid username or password"),
    ("very_long_password", {"username": "alice", "password": "p" * 256}, 401, False, "Invalid username or password"),
    ("numeric_username", {"username": "12345", "password": "password123"}, 401, False, "Invalid username or password"),
    ("special_chars_password", {"username": "alice", "password": "!@#$%^&*()"}, 401, False, "Invalid username or password"),
    ("missing_username", {"password": "password123"}, 422, False, None),
    ("missing_password", {"username": "alice"}, 422, False, None),
    ("null_body", None, 422, False, None),
    ("extra_fields", {"username": "alice", "password": "password123", "role": "admin"}, 200, True, "Login successful"),
    ("unicode_username", {"username": "用户", "password": "password123"}, 401, False, "Invalid username or password"),
    ("whitespace_password", {"username": "alice", "password": "   "}, 400, False, "Password is required"),
]


class TestLoginAPI:
    @pytest.mark.parametrize(
        "case_id,payload,expected_status,expect_success,msg_fragment",
        LOGIN_CASES,
        ids=[c[0] for c in LOGIN_CASES],
    )
    
    def test_login(self, base_url, case_id, payload, expected_status, expect_success, msg_fragment):
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
        from utils.schema_validator import validate_json
        errors = validate_json(data, "login_response.json")
        assert errors == [], errors
        assert isinstance(data["token"], str) and len(data["token"]) > 0
