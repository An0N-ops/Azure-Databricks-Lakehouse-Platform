"""Tests for the Silver conformed-transformation manifest (pure Python).

The Silver manifest is the declarative source of truth for the conformed layer
(ADR-004/ADR-005). These tests pin it to the Bronze manifest (every Silver
table consumes a Bronze table by key) and to the synthetic generator pack
(referenced columns and keys exist), and exercise placeholder resolution.
"""

import copy
from pathlib import Path

import pytest

from notebooks.shared import bronze_manifest, silver_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_MANIFEST_PATH = REPO_ROOT / "pipelines" / "energy" / "bronze_manifest.json"
SILVER_MANIFEST_PATH = REPO_ROOT / "pipelines" / "energy" / "silver_manifest.json"

EXPECTED_ENTITIES = {
    "regions",
    "asset_types",
    "work_order_statuses",
    "employee_roles",
    "part_types",
    "customers",
    "locations",
    "assets",
    "employees",
    "inventory",
    "work_orders",
    "maintenance_events",
    "weather",
    "iot_events",
}

EXPECTED_PRIMARY_KEYS = {
    "regions": "region_id",
    "asset_types": "asset_type_id",
    "work_order_statuses": "status_code",
    "employee_roles": "role_id",
    "part_types": "part_type_id",
    "customers": "customer_id",
    "locations": "location_id",
    "assets": "asset_id",
    "employees": "employee_id",
    "inventory": "item_id",
    "work_orders": "work_order_id",
    "maintenance_events": "event_id",
    "weather": "weather_id",
    "iot_events": "event_id",
}


@pytest.fixture(scope="session")
def bronze_data():
    return bronze_manifest.load_manifest(BRONZE_MANIFEST_PATH)


@pytest.fixture(scope="session")
def silver_data():
    return silver_manifest.load_silver_manifest(SILVER_MANIFEST_PATH)


@pytest.fixture(scope="session")
def silver_specs(silver_data):
    return silver_manifest.table_specs(silver_data)


@pytest.fixture(scope="session")
def entity_schema(industry_config):
    return {
        entity: {field["name"]: field["type"] for field in entity_config["fields"]}
        for entity, entity_config in industry_config["entities"].items()
    }


def _table(silver_data, name):
    for table in silver_data["tables"]:
        if table["name"] == name:
            return table
    raise AssertionError(f"table '{name}' not found in silver manifest")


def test_manifest_loads_and_validates_against_generator(silver_data, entity_schema):
    silver_manifest.validate_silver_manifest(silver_data, entity_schema)
    assert silver_data["metadata"]["pipeline"] == "energy_lakehouse"
    assert silver_data["metadata"]["industry"] == "energy"
    assert silver_data["schema"] == "silver"


def test_manifest_covers_generator_entities(silver_data):
    names = {table["name"] for table in silver_data["tables"]}
    assert names == EXPECTED_ENTITIES


def test_primary_keys_match_generator(silver_data):
    for table in silver_data["tables"]:
        assert table["primary_key"] == EXPECTED_PRIMARY_KEYS[table["name"]]


def test_scd_keys_default_to_primary_key(silver_data):
    for table in silver_data["tables"]:
        assert table["keys"] == [table["primary_key"]]


def test_every_source_references_a_bronze_table(silver_data, bronze_data):
    bronze_names = {table["name"] for table in bronze_data["tables"]}
    for table in silver_data["tables"]:
        source_template = table["source"]["table"]
        bronze_name = source_template.split(".")[-1]
        assert bronze_name in bronze_names, (
            f"{table['name']} references unknown bronze {bronze_name}"
        )


def test_source_resolves_to_bronze_schema(silver_data, silver_specs):
    regions = next(spec for spec in silver_specs if spec["name"] == "regions")
    assert silver_manifest.resolve_source_table(regions) == "dev_lakehouse.bronze.regions"


def test_target_resolves_to_silver_schema(silver_data, silver_specs):
    regions = next(spec for spec in silver_specs if spec["name"] == "regions")
    assert bronze_manifest.target_table_name(silver_data, regions) == "dev_lakehouse.silver.regions"


def test_catalog_override_applies(silver_data, silver_specs, monkeypatch):
    monkeypatch.setenv(bronze_manifest.CATALOG_ENV, "prod_lakehouse")
    regions = next(spec for spec in silver_specs if spec["name"] == "regions")
    assert (
        bronze_manifest.target_table_name(silver_data, regions) == "prod_lakehouse.silver.regions"
    )


def test_conform_columns_exist_in_generator(silver_data, entity_schema):
    for table in silver_data["tables"]:
        fields = entity_schema[table["name"]]
        for column in table.get("conform", {}):
            assert column in fields, f"{table['name']} conform column '{column}' not generated"


def test_conform_rules_are_supported(silver_data):
    for table in silver_data["tables"]:
        for column, rules in table.get("conform", {}).items():
            for rule in rules:
                assert rule["rule"] in silver_manifest.SUPPORTED_CONFORM_RULES, (
                    f"{table['name']}.{column} uses unsupported rule {rule['rule']}"
                )
                if rule["rule"] == "cast":
                    assert rule["type"] in silver_manifest.SUPPORTED_CAST_TYPES


def test_every_table_has_primary_key_expectation(silver_data):
    for table in silver_data["tables"]:
        constraints = {exp["constraint"] for exp in table.get("expectations", [])}
        assert f"{table['primary_key']} IS NOT NULL" in constraints


def test_unknown_conform_rule_rejected(silver_data):
    manifest = copy.deepcopy(silver_data)
    manifest["tables"][0]["conform"]["region_name"].append({"rule": "regexp_replace"})
    with pytest.raises(silver_manifest.ManifestError, match="not supported"):
        silver_manifest.validate_silver_manifest(manifest)


def test_cast_type_rejected(silver_data):
    manifest = copy.deepcopy(silver_data)
    manifest["tables"][0]["conform"]["region_name"] = [{"rule": "cast", "type": "blob"}]
    with pytest.raises(silver_manifest.ManifestError, match="cast rule type"):
        silver_manifest.validate_silver_manifest(manifest)


def test_coalesce_requires_value_rejected(silver_data):
    manifest = copy.deepcopy(silver_data)
    manifest["tables"][0]["conform"]["region_name"] = [{"rule": "coalesce"}]
    with pytest.raises(silver_manifest.ManifestError, match="coalesce rule requires 'value'"):
        silver_manifest.validate_silver_manifest(manifest)


def test_unknown_column_rejected_with_schema(silver_data, entity_schema):
    manifest = copy.deepcopy(silver_data)
    manifest["tables"][0]["conform"]["nope"] = [{"rule": "trim"}]
    with pytest.raises(silver_manifest.ManifestError, match="not a column"):
        silver_manifest.validate_silver_manifest(manifest, entity_schema)


def test_unknown_entity_rejected_with_schema(silver_data, entity_schema):
    manifest = copy.deepcopy(silver_data)
    manifest["tables"][0]["name"] = "zerg"
    with pytest.raises(silver_manifest.ManifestError, match="no matching entity"):
        silver_manifest.validate_silver_manifest(manifest, entity_schema)


def test_duplicate_table_names_rejected(silver_data):
    manifest = copy.deepcopy(silver_data)
    manifest["tables"].append(copy.deepcopy(manifest["tables"][0]))
    with pytest.raises(silver_manifest.ManifestError, match="duplicate table name"):
        silver_manifest.validate_silver_manifest(manifest)


def test_missing_source_table_rejected(silver_data):
    manifest = copy.deepcopy(silver_data)
    del manifest["tables"][0]["source"]["table"]
    with pytest.raises(silver_manifest.ManifestError, match="source.table is required"):
        silver_manifest.validate_silver_manifest(manifest)


def test_missing_keys_rejected(silver_data):
    manifest = copy.deepcopy(silver_data)
    del manifest["tables"][0]["keys"]
    with pytest.raises(silver_manifest.ManifestError, match="keys is required"):
        silver_manifest.validate_silver_manifest(manifest)


def test_empty_conform_list_rejected(silver_data):
    manifest = copy.deepcopy(silver_data)
    manifest["tables"][0]["conform"]["region_name"] = []
    with pytest.raises(silver_manifest.ManifestError, match="must not be empty"):
        silver_manifest.validate_silver_manifest(manifest)


def test_unknown_placeholder_rejected(silver_data):
    manifest = copy.deepcopy(silver_data)
    manifest["tables"][0]["source"]["table"] = "{unknown}.bronze.regions"
    with pytest.raises(silver_manifest.ManifestError, match="unknown placeholder"):
        silver_manifest.validate_silver_manifest(manifest)


def test_load_missing_manifest(tmp_path):
    with pytest.raises(silver_manifest.ManifestError, match="not found"):
        silver_manifest.load_silver_manifest(tmp_path / "missing" / "silver_manifest.json")
