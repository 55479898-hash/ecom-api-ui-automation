"""Shared fixtures and framework wiring."""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from utils.api_client import ApiClient
from utils.config_loader import load_env_config
from utils.db_helper import DbHelper

PROJECT_ROOT = Path(__file__).parent.parent
ECOM_APP_DIR = PROJECT_ROOT / "ecom_app"
_env = load_env_config()
BASE_URL = _env["base_url"]

_server_proc = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _is_server_ready() -> bool:
    import requests
    try:
        return requests.get(f"{BASE_URL}/api/products", timeout=2).status_code == 200
    except Exception:
        return False


def _start_server():
    global _server_proc
    if _is_server_ready():
        return None
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ECOM_APP_DIR)
    kwargs = {"cwd": str(ECOM_APP_DIR), "env": env, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    _server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        **kwargs,
    )
    for _ in range(20):
        if _is_server_ready():
            return _server_proc
        time.sleep(0.3)
    _server_proc.kill()
    raise RuntimeError("Server failed to start within 6 seconds.")


def _stop_server(proc):
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session", autouse=True)
def start_server():
    proc = _start_server()
    yield BASE_URL
    _stop_server(proc)


@pytest.fixture(scope="session")
def env_config():
    return load_env_config()


@pytest.fixture(scope="session")
def base_url(start_server, env_config):
    return env_config["base_url"]


@pytest.fixture(scope="session")
def api_client(base_url):
    return ApiClient(base_url)


@pytest.fixture(scope="session")
def db_helper(env_config):
    return DbHelper(env_config)


@pytest.fixture
def auth_token(api_client):
    return api_client.login("alice", "password123")


@pytest.fixture
def auth_client(api_client, auth_token):
    return api_client.with_token(auth_token)


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
