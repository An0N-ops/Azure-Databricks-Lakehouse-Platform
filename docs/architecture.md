# Platform Architecture

The architecture diagram lives in the [README](../README.md#platform-architecture). This document specifies the components behind it.

## Source Systems & Ingestion

- **Oracle Fusion ERP & Oracle Database 19c**: extracted with Azure Data Factory (ADF) pipeline orchestration, self-hosted integration runtimes (SHIR), and JDBC connectors; Change Data Capture (CDC) for high-frequency updates.
- **SFTP & REST APIs**: semi-structured files (CSV, JSON, XML) ingested with Databricks Auto Loader (`cloudFiles`), providing idempotent ingestion and automatic schema drift detection.
- **Azure Event Hubs**: telemetry and clickstream streams captured with Spark Structured Streaming, checkpointed on ADLS Gen2.

## Medallion Storage (ADLS Gen2 + Delta Lake)

- **Bronze (`raw`)**: append-only landing zone. Preserves raw source records with audit metadata (`_ingested_at`, `_source_file`, `_commit_id`). No transformations.
- **Silver (`cleansed`)**: conformed, validated entities. Schema validation, normalization, SCD Type 1/2 tracking, and DLT quality expectations.
- **Gold (`analytics`)**: Kimball star-schema dimensional models (`dim_*`, `fact_*`) optimized for Databricks SQL Serverless and Power BI.

## Unity Catalog Governance Model

Governance is modeled on the 3-level namespace `catalog.schema.table`:

```text
prod_lakehouse (Catalog)
├── bronze (Schema)   ── oracle_fusion_orders, sftp_financial_records
├── silver (Schema)   ── dim_customer, fact_sales_cleansed
└── gold (Schema)     ── dim_customer_360, fact_monthly_revenue
```

- **Storage credentials** use an Azure User-Assigned Managed Identity to grant access to ADLS Gen2 paths — no storage keys.
- **Fine-grained access** (row/column security, dynamic masking) is applied via Unity Catalog functions and grants.

## Pipeline Framework

Transformations use Delta Live Tables (DLT) / Lakeflow Declarative Pipelines:

- **Declarative ETL**: flow dependencies authored as data (SQL or PySpark `@dlt.table` decorators), reviewable in pull requests.
- **Data quality expectations**: `EXPECT`, `ON VIOLATION DROP ROW`, `ON VIOLATION FAIL UPDATE` gate promotions between layers.
- **Auto-maintenance**: DLT handles `OPTIMIZE`, Z-Ordering, and `VACUUM`.

### Bronze Ingestion Framework

Bronze is ingested with Auto Loader streaming into append-only Delta tables. The landing sources and quality contracts are declared as data in `pipelines/energy/bronze_manifest.json` — one table spec per entity — and rendered by the shared DLT notebook `notebooks/bronze/ingest_energy.py`:

- **Placeholders**: source paths and target names carry `{landing}`, `{catalog}`, `{schema}`, and `{table}` tokens resolved from environment variables (`DATABRICKS_LANDING_PATH`, `DATABRICKS_CATALOG`), so one manifest promotes unchanged across dev/qa/prod (ADR-004).
- **Audit metadata**: every table carries `_ingested_at`, `_source_file`, and `_commit_id` via `notebooks/shared/ingest.py` (`with_audit_columns`).
- **Quality policy**: expectations at the Bronze-to-Silver boundary use the ADR-005 **retain** policy — violating raw rows are preserved and flagged in the DLT event log, never silently dropped.
- **Provenance**: the synthetic generator writes Hive-style `batch_date=YYYY-MM-DD` partitions that Auto Loader surfaces as a partition column, preserving per-batch lineage back to the source.
- **Testing**: manifests are validated by pure-Python tests (`tests/test_bronze_manifest.py`) that pin the manifest to the generator pack, so no Spark runtime is required in CI.

### Silver Conformed Layer

Silver is conformed from Bronze in `notebooks/silver/transform_energy.py`, driven by `pipelines/energy/silver_manifest.json` — one spec per entity declaring its Bronze source, primary/SCD keys, per-column conforming rules, and quality expectations:

- **Conforming rules** are a small declarative vocabulary (`trim`, `lower`, `upper`, `initcap`, `coalesce`, `cast`) applied in declaration order via `notebooks/shared/silver.py` (`apply_conform`), so column hygiene is reviewable as data (ADR-004).
- **SCD Type 1 upsert**: each Silver table is the target of `dlt.apply_changes`, sequenced by `_ingested_at`, so reprocessing Bronze is idempotent. Rows with null keys are ignored by the upsert (`ignore_null_keys`) but remain visible in Bronze.
- **Audit columns**: Bronze metadata is retained and `_updated_at` is added, per `docs/development.md`.
- **Testing**: `tests/test_silver_manifest.py` pins the Silver manifest to both the Bronze manifest (every source table exists) and the generator pack (keys and conformed columns are generated), all pure Python.

Decisions are recorded in [ADR-001](adr/ADR-001-medallion-architecture.md), [ADR-002](adr/ADR-002-unity-catalog.md), and [ADR-004](adr/ADR-004-lakeflow-declarative-pipelines.md).
