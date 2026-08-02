# Synthetic Enterprise Data Generator

Deterministic, config-driven generator for realistic-looking but fully synthetic
enterprise data. It powers the platform's Bronze → Silver → Gold pipelines with a
fictional Oil & Gas operator so end-to-end development and testing never touch
real or PII-bearing records.

## Business Problem

Azure Databricks Lakehouse workloads need realistic data volumes, relationships,
and semantics to build and validate ingestion, medallion transformations,
quality rules, and dashboards. Real production data is unavailable during
development, prohibited in non-production environments, or too sensitive to
share. Teams end up hand-crafting one-off fixture scripts that rot, disagree,
and cannot scale.

## Solution

A **domain-agnostic generator core** plus **industry data packs** declared as
JSON. The core provides reusable field primitives (ids, weighted choices,
ranges, dates, foreign keys, expressions, conditionals) and guarantees:

- **Determinism** — same seed + config ⇒ identical rows, every time.
- **Referential integrity** — foreign keys always resolve to generated rows.
- **Date-partitioned batches** — output is stamped `batch_date=YYYY-MM-DD` so
  Auto Loader can ingest incrementally, with a `manifest.json` recording seed,
  window, and row counts per entity for reproducibility.

The `energy` pack models **NorthGrid Resources**, a fictional Oil & Gas operator:
customers, locations, assets, employees, inventory, work orders, maintenance
events, daily weather, and high-frequency IoT telemetry — 14 related entities.

## Expected Outcome

- A repeatable, version-controlled source of sample data (no fragile fixtures).
- Pipelines can be developed and CI-tested offline, before any Azure resources
  are provisioned.
- Data volumes scale from unit-test size to batch-processing size with one flag
  (`--scale`).
- New domains are added by writing JSON, not Python.

## Dependencies

- Python 3.11 (target), no third-party packages required for CSV/JSON output.
- Optional: `pyarrow` for Parquet output.
- Pytest (dev) — tests live under `tests/` at the repo root.

## Usage

Run from the repo root (module path is `sample-data/sample_data`):

```bash
# List available industry packs
python -m sample_data list

# Generate a full-energy batch (CSV by default)
PYTHONPATH=sample-data python -m sample_data generate --industry energy

# Small, fast batch for local smoke tests
PYTHONPATH=sample-data python -m sample_data generate --seed 42 --scale 0.05

# Narrow the window and choose a batch/ingestion date
PYTHONPATH=sample-data python -m sample_data generate \
  --start-date 2025-01-01 --end-date 2025-12-31 --as-of-date 2025-12-31

# JSON (or Parquet in addition)
PYTHONPATH=sample-data python -m sample_data generate --format json --parquet
```

Output layout (CSV example):

```text
sample-data/output/
  energy/
    manifest.json
    customers/
      batch_date=2026-07-31/customers.csv
    iot_events/
      batch_date=2026-07-31/iot_events.csv
    ...
```

## Adding an Industry Pack

1. Create `sample_data/industries/<industry>/config.json`.
2. Declare `metadata` (industry, company, generation window) and `entities`.
3. Each entity has `volume` (a row count, or `{"rows_per_reference": "...",
   "rows_per_unit": N}` to scale off another entity) and a `fields` list.
4. Reference other entities with `foreign_key` fields; the generator topologically
   orders entities so referenced data always exists first.

Field types: `id`, `choice`, `int_range`, `float_range`, `date_between`,
`datetime_between`, `string_pattern`, `constant`, `foreign_key`, `expression`,
`conditional`. Packs are validated on load; misconfiguration fails fast with
actionable messages.

## Roadmap

- Bronze ingestion (Auto Loader) and Unity Catalog tables for generated output.
- Incremental batch modes (append / event-time windows) for Silver processing.
- Additional industry packs (e.g., manufacturing, retail).
