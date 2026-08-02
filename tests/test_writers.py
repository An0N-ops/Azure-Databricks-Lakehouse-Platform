import csv
import json
from datetime import date

import pytest
from sample_data.writers import write_batch

START = date(2024, 1, 1)
END = date(2026, 7, 31)
AS_OF = date(2026, 7, 31)


def _run(output, data, industry_config, **kwargs):
    return write_batch(
        output,
        "energy",
        data,
        seed=42,
        as_of_date=kwargs.get("as_of_date", AS_OF),
        start_date=kwargs.get("start_date", START),
        end_date=kwargs.get("end_date", END),
        scale=kwargs.get("scale", 1.0),
        metadata=industry_config["metadata"],
        fmt=kwargs.get("fmt", "csv"),
        parquet=kwargs.get("parquet", False),
    )


def test_csv_roundtrip(tmp_path, small_data, industry_config):
    files, _ = _run(tmp_path, small_data, industry_config)
    csv_path = next(path for path in files if path.name == "customers.csv")
    with open(csv_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(small_data["customers"])
    assert rows[0]["customer_id"] == small_data["customers"][0]["customer_id"]
    assert "batch_date=2026-07-31" in str(csv_path)


def test_csv_handles_null_values(tmp_path, small_data, industry_config):
    files, _ = _run(tmp_path, small_data, industry_config)
    csv_path = next(path for path in files if path.name == "work_orders.csv")
    with open(csv_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    completed = [row for row in rows if row["status_code"] != "COMPLETED"]
    assert completed and all(row["actual_hours"] == "" for row in completed)


def test_json_roundtrip(tmp_path, small_data, industry_config):
    files, _ = _run(tmp_path, small_data, industry_config, fmt="json")
    json_path = next(path for path in files if path.name == "regions.json")
    with open(json_path, encoding="utf-8") as handle:
        rows = json.load(handle)
    assert rows == small_data["regions"]


def test_manifest_written(tmp_path, small_data, industry_config):
    _, manifest = _run(tmp_path, small_data, industry_config)
    manifest_path = tmp_path / "energy" / "manifest.json"
    assert manifest_path.is_file()
    assert manifest["seed"] == 42
    assert manifest["industry"] == "energy"
    assert manifest["entity_counts"]["customers"] == len(small_data["customers"])
    assert set(manifest.keys()) >= {
        "generator_version",
        "industry",
        "company",
        "seed",
        "start_date",
        "end_date",
        "as_of_date",
        "scale",
        "entity_counts",
        "generated_at",
    }


def test_manifest_is_valid_json(tmp_path, small_data, industry_config):
    _run(tmp_path, small_data, industry_config)
    with open(tmp_path / "energy" / "manifest.json", encoding="utf-8") as handle:
        json.load(handle)


def test_parquet_when_available(tmp_path, small_data, industry_config):
    pytest.importorskip("pyarrow")
    files, _ = _run(tmp_path, small_data, industry_config, parquet=True)
    assert any(path.suffix == ".parquet" for path in files)


def test_unsupported_format_rejected(tmp_path, small_data, industry_config):
    with pytest.raises(ValueError, match="unsupported output format"):
        _run(tmp_path, small_data, industry_config, fmt="xml")
