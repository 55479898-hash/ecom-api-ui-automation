import os
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent.parent / "config"
DEFAULT_ENV = os.environ.get("TEST_ENV", "test")


def load_env_config(env_name: str | None = None) -> dict:
    env_name = env_name or DEFAULT_ENV
    with open(CONFIG_DIR / "environments.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    cfg = data["environments"][env_name]
    cfg["name"] = env_name
    if os.environ.get("ECOM_BASE_URL"):
        cfg["base_url"] = os.environ["ECOM_BASE_URL"]
    return cfg
