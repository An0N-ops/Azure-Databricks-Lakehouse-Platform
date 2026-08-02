"""Tests for the Bronze ingestion manifest (pure Python, no Spark runtime).

The manifest is the declarative source of truth for Bronze Auto Loader
ingestion (ADR-004). These tests pin the manifest to the synthetic generator
pack (``sample-data/``) so the two stay in lockstep, and exercise placeholder
resolution across dev/qa/prod-style variables.
"""

import copy
from pathlib import Path

import pytest

from notebooks.shared import bronze_manifest

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

LANDING = "abfss://raw@northgrid.dfs.core.windows.net/landing"


@pytest.fixture(scope="session")
def bronze_manifest_path():
    return Path(__file__).resolve().parents[1] / "pipelines" / "energy" / "bronze_manifest.json"


@pytest.fixture(scope="session")
def bronze_manifest_data(bronze_manifest_path):
    return bronze_manifest.load_manifest(bronze_manifest_path)


@pytest.fixture(scope="session")
def energy_specs(bronze_manifest_data):
    return bronze_manifest.table_specs(bronze_manifest_data)


def _table(bronze_manifest_data, name):
    for table in bronze_manifest_data["tables"]:
        if table["name"] == name:
            return table
    raise AssertionError(f"table '{name}' not found in manifest")


def test_manifest_loads_and_validates(bronze_manifest_data):
    bronze_manifest.validate_manifest(bronze_manifest_data)
    assert bronze_manifest_data["metadata"]["pipeline"] == "energy_bronze"
    assert bronze_manifest_data["metadata"]["industry"] == "energy"
    assert bronze_manifest_data["schema"] == "bronze"


def test_manifest_covers_generator_entities(bronze_manifest_data):
    names = {table["name"] for table in bronze_manifest_data["tables"]}
    assert names == EXPECTED_ENTITIES


def test_manifest_has_no_duplicate_table_names(bronze_manifest_data):
    names = [table["name"] for table in bronze_manifest_data["tables"]]
    assert len(names) == len(set(names)) == len(EXPECTED_ENTITIES)


def test_primary_keys_match_generator(bronze_manifest_data):
    for table in bronze_manifest_data["tables"]:
        assert table["primary_key"] == EXPECTED_PRIMARY_KEYS[table["name"]]


def test_defaults_merge_into_effective_specs(energy_specs):
    regions = next(spec for spec in energy_specs if spec["name"] == "regions")
    assert regions["source"]["format"] == "csv"
    assert regions["source"]["options"] == {"header": "true", "inferSchema": "true"}


def test_every_table_has_primary_key_expectation(bronze_manifest_data):
    for table in bronze_manifest_data["tables"]:
        constraints = {exp["constraint"] for exp in table.get("expectations", [])}
        assert f"{table['primary_key']} IS NOT NULL" in constraints


def test_resolve_source_path(energy_specs):
    regions = next(spec for spec in energy_specs if spec["name"] == "regions")
    assert (
        bronze_manifest.resolve_source_path(regions, variables={"landing": LANDING})
        == f"{LANDING}/energy/regions"
    )


def test_resolve_source_path_requires_landing(energy_specs, monkeypatch):
    monkeypatch.delenv(bronze_manifest.LANDING_ENV, raising=False)
    regions = next(spec for spec in energy_specs if spec["name"] == "regions")
    with pytest.raises(bronze_manifest.ManifestError, match="no value for placeholder"):
        bronze_manifest.resolve_source_path(regions)


def test_default_catalog_target_table_name(bronze_manifest_data, energy_specs, monkeypatch):
    monkeypatch.delenv(bronze_manifest.CATALOG_ENV, raising=False)
    regions = next(spec for spec in energy_specs if spec["name"] == "regions")
    assert (
        bronze_manifest.target_table_name(bronze_manifest_data, regions)
        == "dev_lakehouse.bronze.regions"
    )


def test_target_table_name_uses_catalog_override(bronze_manifest_data, energy_specs, monkeypatch):
    monkeypatch.setenv(bronze_manifest.CATALOG_ENV, "qa_lakehouse")
    regions = next(spec for spec in energy_specs if spec["name"] == "regions")
    assert (
        bronze_manifest.target_table_name(bronze_manifest_data, regions)
        == "qa_lakehouse.bronze.regions"
    )


def test_custom_variables_override_environment(energy_specs, monkeypatch):
    monkeypatch.setenv(bronze_manifest.LANDING_ENV, "abfss://wrong@account/landing")
    regions = next(spec for spec in energy_specs if spec["name"] == "regions")
    assert (
        bronze_manifest.resolve_source_path(regions, variables={"landing": LANDING})
        == f"{LANDING}/energy/regions"
    )


def test_unknown_placeholder_rejected(bronze_manifest_data):
    manifest = copy.deepcopy(bronze_manifest_data)
    manifest["tables"][0]["source"]["path"] = "{unknown}/energy/regions"
    with pytest.raises(bronze_manifest.ManifestError, match="unknown placeholder"):
        bronze_manifest.validate_manifest(manifest)


def test_unsupported_format_rejected(bronze_manifest_data):
    manifest = copy.deepcopy(bronze_manifest_data)
    manifest["tables"][0]["source"]["format"] = "orc"
    with pytest.raises(bronze_manifest.ManifestError, match="not supported"):
        bronze_manifest.validate_manifest(manifest)


def test_duplicate_table_names_rejected(bronze_manifest_data):
    manifest = copy.deepcopy(bronze_manifest_data)
    manifest["tables"].append(copy.deepcopy(manifest["tables"][0]))
    with pytest.raises(bronze_manifest.ManifestError, match="duplicate table name"):
        bronze_manifest.validate_manifest(manifest)


def test_invalid_table_name_rejected(bronze_manifest_data):
    manifest = copy.deepcopy(bronze_manifest_data)
    manifest["tables"][0]["name"] = "two words"
    with pytest.raises(bronze_manifest.ManifestError, match="not a valid table name"):
        bronze_manifest.validate_manifest(manifest)


def test_missing_tables_rejected(bronze_manifest_data):
    manifest = copy.deepcopy(bronze_manifest_data)
    del manifest["tables"]
    with pytest.raises(bronze_manifest.ManifestError, match="tables is required"):
        bronze_manifest.validate_manifest(manifest)


def test_missing_metadata_rejected(bronze_manifest_data):
    manifest = copy.deepcopy(bronze_manifest_data)
    del manifest["metadata"]
    with pytest.raises(bronze_manifest.ManifestError, match="metadata is required"):
        bronze_manifest.validate_manifest(manifest)


def test_missing_primary_key_rejected(bronze_manifest_data):
    manifest = copy.deepcopy(bronze_manifest_data)
    del manifest["tables"][0]["primary_key"]
    with pytest.raises(bronze_manifest.ManifestError, match="primary_key is required"):
        bronze_manifest.validate_manifest(manifest)


def test_expectation_duplicate_name_rejected(bronze_manifest_data):
    manifest = copy.deepcopy(bronze_manifest_data)
    table = manifest["tables"][0]
    table["expectations"].append(copy.deepcopy(table["expectations"][0]))
    with pytest.raises(bronze_manifest.ManifestError, match="duplicate name"):
        bronze_manifest.validate_manifest(manifest)


def test_load_missing_manifest(tmp_path):
    with pytest.raises(bronze_manifest.ManifestError, match="not found"):
        bronze_manifest.load_manifest(tmp_path / "missing" / "bronze_manifest.json")


def test_load_invalid_json(tmp_path):
    bad = tmp_path / "bronze_manifest.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.raises(bronze_manifest.ManifestError, match="not valid JSON"):
        bronze_manifest.load_manifest(bad)
