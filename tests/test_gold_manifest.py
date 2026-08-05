"""Tests for the Gold star-schema manifest (pure Python).

The Gold manifest is the declarative source of truth for the analytics layer
(ADR-004/ADR-005). These tests pin it to the Silver manifest (every source is
a Silver table) and to the synthetic generator pack (primary keys, foreign-key
columns, and aggregated measures are actually generated), and exercise the date
dimension generator plus placeholder resolution.
"""

import copy
from pathlib import Path

import pytest

from notebooks.shared import gold_manifest, silver_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_MANIFEST_PATH = REPO_ROOT / "pipelines" / "energy" / "gold_manifest.json"
SILVER_MANIFEST_PATH = REPO_ROOT / "pipelines" / "energy" / "silver_manifest.json"

EXPECTED_TABLES = {
    "dim_region",
    "dim_asset_type",
    "dim_work_order_status",
    "dim_employee_role",
    "dim_part_type",
    "dim_customer",
    "dim_location",
    "dim_asset",
    "dim_employee",
    "dim_date",
    "fact_work_order",
    "fact_maintenance_event",
    "fact_sensor_daily",
    "fact_weather_daily",
}

DIMENSION_SOURCES = {
    "dim_region": "regions",
    "dim_asset_type": "asset_types",
    "dim_work_order_status": "work_order_statuses",
    "dim_employee_role": "employee_roles",
    "dim_part_type": "part_types",
    "dim_customer": "customers",
    "dim_location": "locations",
    "dim_asset": "assets",
    "dim_employee": "employees",
}

FACT_SOURCES = {
    "fact_work_order": "work_orders",
    "fact_maintenance_event": "maintenance_events",
    "fact_sensor_daily": "iot_events",
    "fact_weather_daily": "weather",
}


@pytest.fixture(scope="session")
def gold_data():
    return gold_manifest.load_gold_manifest(GOLD_MANIFEST_PATH)


@pytest.fixture(scope="session")
def gold_specs(gold_data):
    return gold_manifest.table_specs(gold_data)


@pytest.fixture(scope="session")
def entity_schema(industry_config):
    return {
        entity: {field["name"]: field["type"] for field in entity_config["fields"]}
        for entity, entity_config in industry_config["entities"].items()
    }


def _source_entity(table):
    source = table.get("source")
    if source is None:
        return None
    return source["table"].split(".")[-1]


def _table(gold_data, name):
    for table in gold_data["tables"]:
        if table["name"] == name:
            return table
    raise AssertionError(f"table '{name}' not found in gold manifest")


def test_manifest_loads_and_validates_against_generator(gold_data, entity_schema):
    gold_manifest.validate_gold_manifest(gold_data, entity_schema)
    assert gold_data["metadata"]["pipeline"] == "energy_lakehouse"
    assert gold_data["metadata"]["industry"] == "energy"
    assert gold_data["schema"] == "gold"


def test_manifest_covers_expected_models(gold_data):
    names = {table["name"] for table in gold_data["tables"]}
    assert names == EXPECTED_TABLES


def test_dimensions_map_to_silver_entities(gold_data):
    for table in gold_data["tables"]:
        if table["kind"] == "dimension":
            assert table["name"] in DIMENSION_SOURCES
            assert _source_entity(table) == DIMENSION_SOURCES[table["name"]]


def test_facts_map_to_silver_entities(gold_data):
    for table in gold_data["tables"]:
        if table["kind"] == "fact":
            assert table["name"] in FACT_SOURCES
            assert _source_entity(table) == FACT_SOURCES[table["name"]]


def test_every_source_references_a_silver_table(gold_data, gold_specs):
    silver_data = silver_manifest.load_silver_manifest(SILVER_MANIFEST_PATH)
    silver_names = {table["name"] for table in silver_data["tables"]}
    for spec in gold_specs:
        if spec["kind"] == "date_dimension":
            continue
        source = spec["source"]["table"]
        assert source.split(".")[-1] in silver_names, (
            f"{spec['name']} references unknown silver table"
        )


def test_primary_keys_exist_in_generator(gold_data, entity_schema):
    for table in gold_data["tables"]:
        pk_columns = (
            table["primary_key"]
            if isinstance(table["primary_key"], list)
            else [table["primary_key"]]
        )
        entity = _source_entity(table)
        if entity is None:
            assert pk_columns == ["date_key"]
            continue
        fields = entity_schema[entity]
        for column in pk_columns:
            assert column == "date_key" or column in fields, (
                f"{table['name']} primary key column '{column}' not generated"
            )


def test_foreign_keys_reference_known_gold_tables(gold_data):
    names = {table["name"] for table in gold_data["tables"]}
    for table in gold_data["tables"]:
        for fk in table.get("foreign_keys", []):
            assert fk["references"] in names, (
                f"{table['name']} references unknown gold table '{fk['references']}'"
            )


def test_foreign_key_columns_exist_in_generator(gold_data, entity_schema):
    for table in gold_data["tables"]:
        entity = _source_entity(table)
        if entity is None:
            continue
        fields = entity_schema[entity]
        for fk in table.get("foreign_keys", []):
            assert fk["column"] in fields, (
                f"{table['name']} foreign key column '{fk['column']}' not generated"
            )


def test_every_fact_declares_date_key_or_aggregate(gold_data):
    for table in gold_data["tables"]:
        if table["kind"] == "fact":
            assert table.get("date_key") or table.get("aggregate"), (
                f"fact '{table['name']}' declares no date_key or aggregate"
            )


def test_aggregate_group_by_and_measures_exist_in_generator(gold_data, entity_schema):
    for table in gold_data["tables"]:
        aggregate = table.get("aggregate")
        if aggregate is None:
            continue
        fields = entity_schema[_source_entity(table)]
        for column in aggregate["group_by"]:
            assert column in fields, (
                f"{table['name']} aggregate group_by column '{column}' not generated"
            )
        assert aggregate["date_key"]["column"] in fields, (
            f"{table['name']} aggregate date_key column not generated"
        )
        for measure in aggregate["measures"]:
            assert measure["column"] in fields, (
                f"{table['name']} aggregate measure column '{measure['column']}' not generated"
            )


def test_aggregate_aggregations_are_supported(gold_data):
    for table in gold_data["tables"]:
        aggregate = table.get("aggregate")
        if aggregate is None:
            continue
        for measure in aggregate["measures"]:
            assert measure["agg"] in gold_manifest.SUPPORTED_AGGREGATIONS, (
                f"{table['name']} uses unsupported aggregation '{measure['agg']}'"
            )


def test_date_dimension_rows():
    rows = gold_manifest.date_dimension_rows("2024-01-01", "2024-01-03")
    assert len(rows) == 3
    assert [row["date_key"] for row in rows] == [20240101, 20240102, 20240103]
    assert [row["date"] for row in rows] == ["2024-01-01", "2024-01-02", "2024-01-03"]


def test_date_dimension_row_attributes():
    row = gold_manifest.date_dimension_rows("2024-12-25", "2024-12-25")[0]
    assert row["year"] == 2024
    assert row["month"] == 12
    assert row["day"] == 25
    assert row["quarter"] == 4
    assert row["day_of_week"] == 3
    assert row["day_name"] == "Wednesday"
    assert row["is_weekend"] is False


def test_date_dimension_weekend_flag():
    rows = gold_manifest.date_dimension_rows("2024-11-30", "2024-12-01")
    assert [row["is_weekend"] for row in rows] == [True, True]


def test_date_dimension_inverted_range_rejected():
    with pytest.raises(gold_manifest.ManifestError, match="must not be after"):
        gold_manifest.date_dimension_rows("2024-02-02", "2024-02-01")


def test_source_resolves_to_silver_schema(gold_specs):
    dim_region = next(spec for spec in gold_specs if spec["name"] == "dim_region")
    assert gold_manifest.resolve_source_table(dim_region) == "dev_lakehouse.silver.regions"


def test_catalog_override_applies(gold_specs, monkeypatch):
    from notebooks.shared import bronze_manifest

    monkeypatch.setenv(bronze_manifest.CATALOG_ENV, "prod_lakehouse")
    dim_region = next(spec for spec in gold_specs if spec["name"] == "dim_region")
    assert gold_manifest.resolve_source_table(dim_region) == "prod_lakehouse.silver.regions"


def test_duplicate_table_names_rejected(gold_data):
    manifest = copy.deepcopy(gold_data)
    manifest["tables"].append(copy.deepcopy(manifest["tables"][0]))
    with pytest.raises(gold_manifest.ManifestError, match="duplicate table name"):
        gold_manifest.validate_gold_manifest(manifest)


def test_unknown_kind_rejected(gold_data):
    manifest = copy.deepcopy(gold_data)
    manifest["tables"][0]["kind"] = "view"
    with pytest.raises(gold_manifest.ManifestError, match="not supported"):
        gold_manifest.validate_gold_manifest(manifest)


def test_missing_source_rejected(gold_data):
    manifest = copy.deepcopy(gold_data)
    del manifest["tables"][0]["source"]["table"]
    with pytest.raises(gold_manifest.ManifestError, match="source.table is required"):
        gold_manifest.validate_gold_manifest(manifest)


def test_unknown_placeholder_rejected(gold_data):
    manifest = copy.deepcopy(gold_data)
    manifest["tables"][0]["source"]["table"] = "{unknown}.silver.regions"
    with pytest.raises(gold_manifest.ManifestError, match="unknown placeholder"):
        gold_manifest.validate_gold_manifest(manifest)


def test_unknown_aggregation_rejected(gold_data):
    manifest = copy.deepcopy(gold_data)
    sensor = _table(manifest, "fact_sensor_daily")
    sensor["aggregate"]["measures"][0]["agg"] = "median"
    with pytest.raises(gold_manifest.ManifestError, match="not supported"):
        gold_manifest.validate_gold_manifest(manifest)


def test_foreign_key_unknown_gold_table_rejected(gold_data):
    manifest = copy.deepcopy(gold_data)
    customer = _table(manifest, "dim_customer")
    customer["foreign_keys"][0]["references"] = "dim_nope"
    with pytest.raises(gold_manifest.ManifestError, match="unknown gold table"):
        gold_manifest.validate_gold_manifest(manifest)


def test_unknown_fk_column_rejected_with_schema(gold_data, entity_schema):
    manifest = copy.deepcopy(gold_data)
    customer = _table(manifest, "dim_customer")
    customer["foreign_keys"][0]["column"] = "nope"
    with pytest.raises(gold_manifest.ManifestError, match="not a column"):
        gold_manifest.validate_gold_manifest(manifest, entity_schema)


def test_unknown_primary_key_column_rejected_with_schema(gold_data, entity_schema):
    manifest = copy.deepcopy(gold_data)
    region = _table(manifest, "dim_region")
    region["primary_key"] = "nope"
    with pytest.raises(gold_manifest.ManifestError, match="not a column"):
        gold_manifest.validate_gold_manifest(manifest, entity_schema)


def test_invalid_date_range_rejected(gold_data):
    manifest = copy.deepcopy(gold_data)
    _table(manifest, "dim_date")["date_range"]["start"] = "2024-13-45"
    with pytest.raises(gold_manifest.ManifestError, match="ISO dates"):
        gold_manifest.validate_gold_manifest(manifest)


def test_load_missing_manifest(tmp_path):
    with pytest.raises(gold_manifest.ManifestError, match="not found"):
        gold_manifest.load_gold_manifest(tmp_path / "missing" / "gold_manifest.json")
