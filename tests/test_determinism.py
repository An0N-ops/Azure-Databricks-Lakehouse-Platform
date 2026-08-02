from datetime import date

from sample_data.engine import generate


def test_same_seed_identical(small_config):
    first = generate(small_config, seed=7)
    second = generate(small_config, seed=7)
    assert first == second


def test_different_seed_differs(small_config):
    first = generate(small_config, seed=7)
    second = generate(small_config, seed=8)
    assert first["work_orders"] != second["work_orders"]


def test_entities_isolated_from_unrelated_changes(small_config):
    import copy

    baseline = generate(small_config, seed=1)
    changed = copy.deepcopy(small_config)
    changed["entities"]["iot_events"]["volume"]["rows_per_unit"] = 10
    other = generate(changed, seed=1)
    assert baseline["regions"] == other["regions"]
    assert baseline["customers"] == other["customers"]


def test_scale_never_produces_zero_rows(small_config):
    data = generate(small_config, seed=1, scale=0.000001)
    for rows in data.values():
        assert len(rows) >= 1


def test_scale_reduces_volumes(small_config):
    full = generate(small_config, seed=1)
    scaled = generate(small_config, seed=1, scale=0.5)
    assert len(scaled["customers"]) <= len(full["customers"])


def test_bounds_override_applies(small_config):
    data = generate(small_config, seed=3, start_date="2025-01-01", end_date="2025-01-05")
    for row in data["weather"]:
        observed = date.fromisoformat(row["observed_date"])
        assert date(2025, 1, 1) <= observed <= date(2025, 1, 5)


def test_entities_in_dependency_order(small_data):
    keys = list(small_data.keys())
    assert keys.index("regions") < keys.index("customers")
    assert keys.index("locations") < keys.index("assets")
    assert keys.index("assets") < keys.index("work_orders")
    assert keys.index("assets") < keys.index("iot_events")
    assert keys[-1] == "iot_events"
