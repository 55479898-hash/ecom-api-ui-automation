"""Load parameterized test data from JSON files under automation_tests/data/."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def _resolve_value(value):
    if isinstance(value, dict):
        if set(value) == {"__repeat__"}:
            spec = value["__repeat__"]
            return spec["char"] * spec["count"]
        return {k: _resolve_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value(v) for v in value]
    return value


def load_test_cases(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    with open(path, encoding="utf-8") as f:
        cases = json.load(f)
    for case in cases:
        if "payload" in case:
            case["payload"] = _resolve_value(case["payload"])
    return cases
