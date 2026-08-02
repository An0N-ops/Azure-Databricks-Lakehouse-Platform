import copy

import pytest
from sample_data.config import ConfigError, load_config, resolve_entity_order


def _copy(config):
    return copy.deepcopy(config)


def _field(config, entity, name):
    for field in config["entities"][entity]["fields"]:
        if field["name"] == name:
            return field
    raise AssertionError(f"field {entity}.{name} not found")


def test_valid_config_loads(industry_config):
    assert industry_config["metadata"]["industry"] == "energy"
    assert "iot_events" in industry_config["entities"]


def test_metadata_required(industry_config):
    config = _copy(industry_config)
    del config["metadata"]
    with pytest.raises(ConfigError, match="metadata"):
        validate(config)


def validate(config):
    from sample_data.config import validate_config

    validate_config(config)


def test_missing_company(industry_config):
    config = _copy(industry_config)
    del config["metadata"]["company"]
    with pytest.raises(ConfigError, match="company"):
        validate(config)


def test_unknown_field_type(industry_config):
    config = _copy(industry_config)
    _field(config, "regions", "region_name")["type"] = "bogus"
    with pytest.raises(ConfigError, match="unsupported field type"):
        validate(config)


def test_duplicate_field_name(industry_config):
    config = _copy(industry_config)
    config["entities"]["regions"]["fields"].append(
        {"name": "region_id", "type": "constant", "value": "x"}
    )
    with pytest.raises(ConfigError, match="duplicate field"):
        validate(config)


def test_unknown_fk_entity(industry_config):
    config = _copy(industry_config)
    _field(config, "assets", "location_id")["entity"] = "nonexistent"
    with pytest.raises(ConfigError, match="unknown foreign key entity"):
        validate(config)


def test_unknown_fk_column(industry_config):
    config = _copy(industry_config)
    _field(config, "assets", "location_id")["column"] = "nope"
    with pytest.raises(ConfigError, match="has no column"):
        validate(config)


def test_conditional_condition_must_precede(industry_config):
    config = _copy(industry_config)
    _field(config, "work_orders", "actual_hours")["field"] = "completed_at"
    with pytest.raises(ConfigError, match="must appear earlier"):
        validate(config)


def test_expression_unknown_reference(industry_config):
    config = _copy(industry_config)
    _field(config, "employees", "email")["template"] = "{middle_name}@northgridresources.com"
    with pytest.raises(ConfigError, match="must appear earlier"):
        validate(config)


def test_bad_volume(industry_config):
    config = _copy(industry_config)
    config["entities"]["regions"]["volume"] = "many"
    with pytest.raises(ConfigError, match="volume"):
        validate(config)


def test_load_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "missing" / "config.json")


def test_entity_order_fk_before_dependents(industry_config):
    order = resolve_entity_order(industry_config)
    index = {name: i for i, name in enumerate(order)}
    assert index["regions"] < index["customers"]
    assert index["customers"] < index["assets"]
    assert index["locations"] < index["assets"]
    assert index["assets"] < index["work_orders"]
    assert index["assets"] < index["iot_events"]
    assert order[-1] == "iot_events"


def test_entity_order_detects_cycle(industry_config):
    config = _copy(industry_config)
    _field(config, "regions", "country")["type"] = "foreign_key"
    _field(config, "regions", "country")["entity"] = "customers"
    _field(config, "regions", "country")["column"] = "customer_id"
    with pytest.raises(ConfigError, match="cycle"):
        validate(config)
