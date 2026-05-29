import logging
from typing import Any

import requests

logger = logging.getLogger("api_client")


class ApiClient:
    def __init__(self, base_url: str, default_headers: dict | None = None, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {}
        self.timeout = timeout

    def _log(self, method: str, url: str, **kwargs: Any) -> None:
        logger.info("%s %s params=%s json=%s", method, url, kwargs.get("params"), kwargs.get("json"))

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = {**self.default_headers, **kwargs.pop("headers", {})}
        kwargs.setdefault("timeout", self.timeout)
        self._log(method, url, **kwargs)
        resp = requests.request(method, url, headers=headers, **kwargs)
        logger.info("response status=%s body=%s", resp.status_code, resp.text[:500])
        return resp

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def login(self, username: str, password: str) -> str:
        resp = self.post("/api/auth/login", json={"username": username, "password": password})
        resp.raise_for_status()
        return resp.json()["token"]

    def with_token(self, token: str) -> "ApiClient":
        headers = {**self.default_headers, "Authorization": f"Bearer {token}"}
        return ApiClient(self.base_url, headers, self.timeout)
