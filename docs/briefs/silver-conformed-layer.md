# Feature Brief: Silver Conformed Layer

The **Silver layer** conforms validated Bronze entities into clean, normalized,
deduplicated tables with stable business keys.

## Business Problem

Bronze preserves raw records verbatim by design, but analytics cannot consume
raw data: values arrive with inconsistent casing, whitespace, mixed types, and
duplicate or null keys. Without a conformed layer, every downstream model
re-implements the same cleaning and key resolution — and each implementation
diverges, producing "one truth per query". Teams also need reprocessing to be
**safe**: re-running a pipeline against the same source must update state, not
duplicate it.

## Solution

A **declarative conforming framework**: `pipelines/energy/silver_manifest.json`
(ADR-004) declares one spec per entity — its Bronze source, primary/SCD keys,
per-column conforming rules, and DLT quality expectations. A data-driven DLT
notebook (`notebooks/silver/transform_energy.py`) renders one conformed table
per spec:

- **Conforming rules** are a small declarative vocabulary (`trim`, `lower`,
  `upper`, `initcap`, `coalesce`, `cast`) applied in declaration order
  (`notebooks/shared/silver.py`), so column hygiene is reviewable as data.
- **SCD Type 1 upsert**: each table is the target of `dlt.apply_changes`,
  sequenced by `_ingested_at`, so reprocessing Bronze is idempotent and the
  latest state is maintained. Rows with null keys are ignored by the upsert
  (`ignore_null_keys`) but remain visible in Bronze.
- **Audit columns**: Bronze provenance metadata is retained and `_updated_at`
  is added per `docs/development.md`.
- **Quality policy**: the Bronze-to-Silver boundary uses the ADR-005 **retain**
  policy — violating rows are kept and flagged in the DLT event log, never
  silently dropped.

## Expected Outcome

- **One conformed source of truth** per entity, with stable natural keys that
  downstream models join on.
- **Idempotent upserts** — reprocessing updates rather than duplicates.
- **Cleaning is declarative and reviewable** — a PR shows the conforming rules,
  not imperative string handling.
- **No data silently lost** at the conformed boundary — raw provenance always
  survives in Bronze.

## Dependencies

- Bronze tables produced by the ingestion framework (PR 2).
- Delta Live Tables on Databricks Runtime 14.3 LTS+ (ADR-005).
- Unity Catalog `bronze` and `silver` schemas; `DATABRICKS_CATALOG` variable.

## Implementation

- `pipelines/energy/silver_manifest.json` — declarative table specs (source,
  `keys`, `conform` rules, expectations).
- `notebooks/shared/silver_manifest.py` — pure-Python validation (conforming
  vocabulary, cast types, key/column pinning to the generator pack) and
  placeholder resolution.
- `notebooks/shared/silver.py` — PySpark helpers: `apply_conform`,
  `with_updated_at`, `conformed_bronze`, `register_silver` (conformed prep
  table + `dlt.apply_changes` SCD Type 1 upsert).
- `notebooks/silver/transform_energy.py` — the data-driven DLT pipeline
  notebook.
- `tests/test_silver_manifest.py` — pins the manifest to both the Bronze
  manifest (every source exists) and the generator pack (keys and conformed
  columns are generated).

As with Bronze, the Energy pack is the reference implementation; the conforming
framework itself is domain-agnostic.
