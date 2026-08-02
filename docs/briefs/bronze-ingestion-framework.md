# Feature Brief: Bronze Ingestion Framework

Every feature in this platform is documented as a consulting brief — the
business problem it solves, the solution, the expected outcome, and how it is
implemented. This is the **Bronze Ingestion Framework** (landing, raw
ingestion, audit metadata, incremental processing).

## Business Problem

Raw data arrives from heterogeneous, on-premises sources — Oracle ERP exports,
SFTP flat files, REST APIs, and Event Hubs telemetry. Historically each source
gets its own hand-coded ingestion notebook, which:

- **Cannot be reviewed** — the data flow is buried in imperative code, and a
  pull request shows a diff of code, not the contract of what is ingested.
- **Does not promote** — source paths and target names are hard-coded, so every
  environment (dev/qa/prod) forks and drifts.
- **Loses provenance** — raw records are transformed or dropped inline, so a
  downstream defect cannot be traced back to the source row.
- **Is not idempotent** — re-running ingestion can duplicate or re-process data.

Raw records must also be preserved **verbatim** at the Bronze boundary: the
lakehouse is the system of record, so anything the platform later rejects must
still be inspectable.

## Solution

A **declarative ingestion framework**: the source contract lives in
`pipelines/energy/bronze_manifest.json` (ADR-004) — one table spec per entity
declaring its landing source, format/options, and DLT quality expectations.
A data-driven DLT notebook (`notebooks/bronze/ingest_energy.py`) renders one
Auto Loader streaming table per spec.

- **Auto Loader (`cloudFiles`)**: incrementally discovers new files in
  date-partitioned landing paths and tracks processed files in a checkpoint, so
  re-running the pipeline is idempotent.
- **Audit metadata**: every row carries `_ingested_at`, `_source_file`, and
  `_commit_id`, plus the generator's `batch_date` partition, preserving
  per-batch lineage back to the source (see `docs/architecture.md`).
- **Placeholders**: paths and targets carry `{landing}`, `{catalog}`,
  `{schema}`, `{table}` tokens resolved from environment variables, so one
  manifest promotes unchanged across dev/qa/prod.
- **Quality policy**: expectations use the ADR-005 **retain** policy — raw rows
  that violate expectations are kept and flagged in the DLT event log, never
  silently dropped.

## Expected Outcome

- Ingestion contracts are **reviewable as data** — a PR shows what changed in
  the manifest, not a rewrite of PySpark.
- **Idempotent, incremental ingestion** with no duplicate processing on rerun.
- **End-to-end provenance** from landing file to Bronze row, in every record.
- Manifests are **validated in CI without a Spark runtime** (pure-Python tests),
  so defects fail fast at review time rather than at runtime.

## Dependencies

- Delta Live Tables on Databricks Runtime 14.3 LTS+ (ADR-005).
- A Unity Catalog target schema (provisioned in Phase 2).
- Environment variables: `DATABRICKS_LANDING_PATH`, `DATABRICKS_CATALOG`.
- Synthetic landing files produced by the data generator (PR 1).

## Implementation

- `pipelines/energy/bronze_manifest.json` — declarative table specs (source
  path, format, options, expectations) plus shared defaults.
- `notebooks/shared/bronze_manifest.py` — pure-Python loading, validation
  (vocabulary, placeholder allow-list, duplicate detection) and
  placeholder resolution.
- `notebooks/shared/ingest.py` — PySpark helpers: `with_audit_columns`,
  `autoloader_reader`, `bronze_stream`, `dlt_bronze_table`,
  `apply_expectations` (retain policy).
- `notebooks/bronze/ingest_energy.py` — the data-driven DLT pipeline notebook.
- `tests/test_bronze_manifest.py` — pins the manifest to the generator pack
  (entity coverage, primary keys) and exercises placeholder resolution.

The Energy pack demonstrates the framework with the fictional NorthGrid
Resources operator; a new industry is added by writing a new manifest and
landing files, not new pipeline code.
