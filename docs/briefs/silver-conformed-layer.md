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
- **SCD upserts** via `dlt.apply_changes`, sequenced by `_ingested_at`:
  reprocessing Bronze is idempotent and the latest state is maintained.
  Tables default to **SCD Type 1** (`keys` only); a spec opts into **SCD
  Type 2** with `"scd_type": 2` and `track_by` — the list of lifecycle
  attributes whose change closes the current version and opens a new one
  (DLT `stored_as_scd_type=2`). Tracked attributes unchanged: the change is
  absorbed into the current version; repeated identical records create no
  history. The semantics are pinned as a pure-Python oracle in
  `notebooks/shared/scd2.py` (tests in `tests/test_scd2.py`). Rows with null
  keys are ignored by the upsert (`ignore_null_keys`) but remain visible in
  Bronze.
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
  `keys`, optional `scd_type`/`track_by` for SCD Type 2, `conform` rules,
  expectations).
- `notebooks/shared/silver_manifest.py` — pure-Python validation (conforming
  vocabulary, cast types, SCD typing rules, key/column pinning to the
  generator pack) and placeholder resolution.
- `notebooks/shared/scd2.py` — pure-Python SCD Type 2 semantics oracle used
  by the test suite to pin the behavior the DLT engine must produce.
- `notebooks/shared/silver.py` — PySpark helpers: `apply_conform`,
  `with_updated_at`, `conformed_bronze`, `register_silver` (conformed prep
  table + `dlt.apply_changes` SCD upsert, SCD Type 1 or 2 from the spec).
- `notebooks/silver/transform_energy.py` — the data-driven DLT pipeline
  notebook.
- `tests/test_silver_manifest.py` — pins the manifest to both the Bronze
  manifest (every source exists) and the generator pack (keys and conformed
  columns are generated).
- `tests/test_scd2.py` — SCD Type 2 semantics (initial version, close/open,
  current flag, repeated-record no-op) and manifest wiring (only `customers`
  and `assets` opt in; `track_by` columns must exist and be conformed).

As with Bronze, the Energy pack is the reference implementation; the conforming
framework itself is domain-agnostic.
