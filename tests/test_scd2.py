"""Tests for SCD Type 2 semantics and manifest wiring (pure Python).

Two layers are pinned here:

1. The semantics oracle (:func:`notebooks.shared.scd2.apply_scd2`) — the
   behavior contract that DLT's ``track_by`` + ``stored_as_scd_type=2``
   must produce: initial versions, version closing/opening on tracked
   attribute changes, one current version per key, and no history growth
   for repeated identical records.
2. The manifest wiring: exactly the customer and asset entities opt into
   SCD2 for the Energy pack, their ``track_by`` columns exist in the
   generator pack, and the validator rejects malformed SCD2 declarations.
"""

import copy
from pathlib import Path

import pytest

from notebooks.shared import silver_manifest
from notebooks.shared.scd2 import EFFECTIVE_FROM, EFFECTIVE_TO, IS_CURRENT, apply_scd2

REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER_MANIFEST_PATH = REPO_ROOT / "pipelines" / "energy" / "silver_manifest.json"

KEYS = ["customer_id"]
SEQUENCE_BY = "_ingested_at"
# account_status is the only tracked attribute in these unit scenarios; the
# Energy pack tracks account_status + credit_rating.
TRACK_BY = ["account_status"]


def _change(sequence: str, customer_id: str = "CUS00001", **attributes) -> dict:
    row = {"customer_id": customer_id, "company_name": "Apex PetroResources", **attributes}
    row[SEQUENCE_BY] = sequence
    return row


def _customers(sequence: str, customer_id: str, account_status: str) -> dict:
    return _change(sequence, customer_id, account_status=account_status)


def test_initial_record_creates_version():
    versions = apply_scd2(
        [_customers("2026-08-01T00:00:00", "CUS00001", "ACTIVE")],
        keys=KEYS,
        track_by=TRACK_BY,
        sequence_by=SEQUENCE_BY,
    )
    assert len(versions) == 1
    version = versions[0]
    assert version["customer_id"] == "CUS00001"
    assert version["account_status"] == "ACTIVE"
    assert version[EFFECTIVE_FROM] == "2026-08-01T00:00:00"
    assert version[EFFECTIVE_TO] is None
    assert version[IS_CURRENT] is True


def test_changed_record_creates_new_version():
    versions = apply_scd2(
        [
            _customers("2026-08-01T00:00:00", "CUS00001", "ACTIVE"),
            _customers("2026-08-05T00:00:00", "CUS00001", "PAUSED"),
        ],
        keys=KEYS,
        track_by=TRACK_BY,
        sequence_by=SEQUENCE_BY,
    )
    assert len(versions) == 2
    assert [version["account_status"] for version in versions] == ["ACTIVE", "PAUSED"]


def test_previous_version_closed():
    versions = apply_scd2(
        [
            _customers("2026-08-01T00:00:00", "CUS00001", "ACTIVE"),
            _customers("2026-08-05T00:00:00", "CUS00001", "PAUSED"),
        ],
        keys=KEYS,
        track_by=TRACK_BY,
        sequence_by=SEQUENCE_BY,
    )
    assert versions[0][EFFECTIVE_TO] == "2026-08-05T00:00:00"
    assert versions[1][EFFECTIVE_FROM] == "2026-08-05T00:00:00"
    assert versions[0][EFFECTIVE_TO] == versions[1][EFFECTIVE_FROM]
    assert versions[1][EFFECTIVE_TO] is None


def test_exactly_one_current_version_per_key():
    versions = apply_scd2(
        [
            _customers("2026-08-01T00:00:00", "CUS00001", "ACTIVE"),
            _customers("2026-08-05T00:00:00", "CUS00001", "PAUSED"),
            _customers("2026-08-10T00:00:00", "CUS00001", "ACTIVE"),
            _customers("2026-08-02T00:00:00", "CUS00002", "ACTIVE"),
            _customers("2026-08-09T00:00:00", "CUS00002", "PAUSED"),
        ],
        keys=KEYS,
        track_by=TRACK_BY,
        sequence_by=SEQUENCE_BY,
    )
    current = [version for version in versions if version[IS_CURRENT]]
    assert len(current) == 2
    assert {version["customer_id"] for version in current} == {"CUS00001", "CUS00002"}
    assert current[0]["account_status"] == "ACTIVE"
    assert current[1]["account_status"] == "PAUSED"


def test_repeated_identical_record_does_not_create_history():
    versions = apply_scd2(
        [
            _customers("2026-08-01T00:00:00", "CUS00001", "ACTIVE"),
            _customers("2026-08-05T00:00:00", "CUS00001", "ACTIVE"),
            _customers("2026-08-09T00:00:00", "CUS00001", "ACTIVE"),
        ],
        keys=KEYS,
        track_by=TRACK_BY,
        sequence_by=SEQUENCE_BY,
    )
    assert len(versions) == 1
    assert versions[0][IS_CURRENT] is True
    assert versions[0][EFFECTIVE_TO] is None


def test_untracked_attribute_change_does_not_create_version():
    versions = apply_scd2(
        [
            _change("2026-08-01T00:00:00", "CUS00001", account_status="ACTIVE", segment="UPSTREAM"),
            _change(
                "2026-08-05T00:00:00", "CUS00001", account_status="ACTIVE", segment="DOWNSTREAM"
            ),
        ],
        keys=KEYS,
        track_by=TRACK_BY,
        sequence_by=SEQUENCE_BY,
    )
    assert len(versions) == 1
    assert versions[0][IS_CURRENT] is True
    assert versions[0]["segment"] == "DOWNSTREAM"


def test_multiple_tracked_attributes_any_change_opens_version():
    versions = apply_scd2(
        [
            _change("2026-08-01T00:00:00", "CUS00001", account_status="ACTIVE", credit_rating="AA"),
            _change("2026-08-05T00:00:00", "CUS00001", account_status="ACTIVE", credit_rating="A+"),
        ],
        keys=KEYS,
        track_by=["account_status", "credit_rating"],
        sequence_by=SEQUENCE_BY,
    )
    assert len(versions) == 2
    assert [version["credit_rating"] for version in versions] == ["AA", "A+"]


def test_null_keys_are_ignored():
    versions = apply_scd2(
        [
            _customers("2026-08-01T00:00:00", "CUS00001", "ACTIVE"),
            _change("2026-08-05T00:00:00", customer_id=None, account_status="PAUSED"),
        ],
        keys=KEYS,
        track_by=TRACK_BY,
        sequence_by=SEQUENCE_BY,
    )
    assert len(versions) == 1
    assert versions[0]["customer_id"] == "CUS00001"
    assert versions[0][IS_CURRENT] is True


def test_composite_business_key_supported():
    versions = apply_scd2(
        [
            _change(
                "2026-08-01T00:00:00",
                "AS000001",
                location_id="LOC00001",
                part_type_id="PRT003",
                quantity_on_hand=100,
            ),
            _change(
                "2026-08-04T00:00:00",
                "AS000001",
                location_id="LOC00001",
                part_type_id="PRT003",
                quantity_on_hand=80,
            ),
        ],
        keys=["location_id", "part_type_id"],
        track_by=["quantity_on_hand"],
        sequence_by=SEQUENCE_BY,
    )
    assert len(versions) == 2
    assert [v["quantity_on_hand"] for v in versions] == [100, 80]
    assert versions[0][EFFECTIVE_TO] == versions[1][EFFECTIVE_FROM]


# ---------------------------------------------------------------------------
# Manifest wiring


@pytest.fixture(scope="session")
def silver_data():
    return silver_manifest.load_silver_manifest(SILVER_MANIFEST_PATH)


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


def test_scd2_declared_only_for_customers_and_assets(silver_data):
    scd2_tables = {
        table["name"] for table in silver_data["tables"] if int(table.get("scd_type", 1)) == 2
    }
    assert scd2_tables == {"customers", "assets"}


def test_scd2_tables_track_lifecycle_attributes(silver_data):
    customers = _table(silver_data, "customers")
    assert customers["scd_type"] == 2
    assert customers["track_by"] == ["account_status", "credit_rating"]
    assets = _table(silver_data, "assets")
    assert assets["scd_type"] == 2
    assert assets["track_by"] == ["asset_status", "criticality"]


def test_scd1_tables_have_no_track_by(silver_data):
    for table in silver_data["tables"]:
        if int(table.get("scd_type", 1)) == 1:
            assert "track_by" not in table


def test_manifest_with_scd2_validates_against_generator(silver_data, entity_schema):
    silver_manifest.validate_silver_manifest(silver_data, entity_schema)


def test_scd2_requires_track_by(silver_data):
    manifest = copy.deepcopy(silver_data)
    del _table(manifest, "customers")["track_by"]
    with pytest.raises(silver_manifest.ManifestError, match="track_by must be a non-empty list"):
        silver_manifest.validate_silver_manifest(manifest)


def test_track_by_only_allowed_with_scd2(silver_data):
    manifest = copy.deepcopy(silver_data)
    _table(manifest, "regions")["track_by"] = ["region_name"]
    with pytest.raises(silver_manifest.ManifestError, match="only allowed with scd_type 2"):
        silver_manifest.validate_silver_manifest(manifest)


def test_scd_type_must_be_1_or_2(silver_data):
    manifest = copy.deepcopy(silver_data)
    _table(manifest, "regions")["scd_type"] = 3
    with pytest.raises(silver_manifest.ManifestError, match="not supported"):
        silver_manifest.validate_silver_manifest(manifest)


def test_scd_type_accepts_numeric_string(silver_data, entity_schema):
    manifest = copy.deepcopy(silver_data)
    _table(manifest, "customers")["scd_type"] = "2"
    silver_manifest.validate_silver_manifest(manifest, entity_schema)


def test_track_by_column_must_exist_in_generator(silver_data, entity_schema):
    manifest = copy.deepcopy(silver_data)
    _table(manifest, "customers")["track_by"] = ["nope"]
    with pytest.raises(silver_manifest.ManifestError, match="not a column"):
        silver_manifest.validate_silver_manifest(manifest, entity_schema)


def test_track_by_columns_are_conformed(silver_data):
    for name in ("customers", "assets"):
        table = _table(silver_data, name)
        for column in table["track_by"]:
            assert column in table.get("conform", {}), (
                f"{name} SCD2 track column '{column}' is not conformed"
            )
