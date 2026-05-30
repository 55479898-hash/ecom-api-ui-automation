"""Run product-list assertions defined in JSON test data."""


def run_product_assertions(data: list, assertions: list[dict] | None, case_id: str) -> None:
    if not assertions:
        return
    for rule in assertions:
        _run_one(data, rule, case_id)


def _run_one(data: list, rule: dict, case_id: str) -> None:
    kind = rule["type"]

    if kind == "list_length":
        assert len(data) == rule["equals"], f"[{case_id}] expected length {rule['equals']}, got {len(data)}"
    elif kind == "list_min_length":
        assert len(data) >= rule["min"], f"[{case_id}] expected min length {rule['min']}"
    elif kind == "all_field_equals":
        field, value = rule["field"], rule["value"]
        assert all(item[field] == value for item in data), f"[{case_id}] not all {field} == {value}"
    elif kind == "all_field_gte":
        field, value = rule["field"], rule["value"]
        assert all(item[field] >= value for item in data), f"[{case_id}] not all {field} >= {value}"
    elif kind == "all_field_lte":
        field, value = rule["field"], rule["value"]
        assert all(item[field] <= value for item in data), f"[{case_id}] not all {field} <= {value}"
    elif kind == "all_field_between":
        field, low, high = rule["field"], rule["min"], rule["max"]
        assert all(low <= item[field] <= high for item in data), f"[{case_id}] {field} not in [{low}, {high}]"
    elif kind == "any_field_contains":
        field, text = rule["field"], rule["contains"]
        assert any(text in item[field] for item in data), f"[{case_id}] no {field} contains {text!r}"
    elif kind == "is_list":
        assert isinstance(data, list), f"[{case_id}] response is not a list"
    else:
        raise ValueError(f"Unknown assertion type: {kind}")
