import json
from pathlib import Path

from jsonschema import Draft7Validator

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def load_schema(name: str) -> dict:
    with open(SCHEMA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def validate_json(data, schema_name: str) -> list[str]:
    schema = load_schema(schema_name)
    validator = Draft7Validator(schema)
    return [e.message for e in validator.iter_errors(data)]
