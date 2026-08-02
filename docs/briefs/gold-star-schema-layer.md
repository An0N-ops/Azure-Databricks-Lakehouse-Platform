# Feature Brief: Gold Star-Schema Layer

The **Gold layer** turns conformed Silver entities into analytics-ready Kimball
star-schema models (`dim_*`, `fact_*`) optimized for Databricks SQL Serverless
and BI tools.

## Business Problem

Business users and BI tools do not want normalized operational tables — they
want **query-ready, trustworthy models** that answer questions at a declared
grain. In the Energy reference, those questions are operational and executive:
downtime by asset, work-order status flow, sensor alert trends, and weather
context around field activity. Without a governed modeling layer, analysts
hand-join operational tables in every query, re-derive date keys inconsistently,
and — worst of all — can be served a **broken fact table** that a bad
transformation silently published.

## Solution

A **declarative Kimball star schema**: `pipelines/energy/gold_manifest.json`
(ADR-004) declares one spec per model — its Silver source, kind (dimension,
date dimension, or fact), primary key, foreign-key references, and for facts a
derived date key plus optional aggregations. A data-driven DLT notebook
(`notebooks/gold/transform_energy.py`) renders one DLT table per model:

- **Dimensions** conform Silver entities as `dim_*` tables; the manifest's
  foreign-key declarations make the star schema reviewable as data. `dim_date`
  is generated from a declared date range
  (`notebooks/shared/gold_manifest.py`, `date_dimension_rows`) and shares the
  `YYYYMMDD` integer key used by the facts.
- **Facts** derive `date_key` from a declared timestamp/date column so they join
  directly to `dim_date`. `fact_sensor_daily` demonstrates an aggregate fact:
  measures (`avg`, `min`, `max`, `count_true`) are collapsed to a declared
  grain (asset × sensor type × day).
- **Quality policy**: the Silver-to-Gold boundary uses the ADR-005 **fail**
  policy (`notebooks/shared/gold.py`, `register_gold`) — an update that
  violates a Gold expectation **aborts the pipeline** rather than publishing a
  broken analytics table.

## Expected Outcome

- **Analytics-ready models** joinable on `date_key` and declared foreign keys,
  with no per-query re-derivation.
- **Trustworthy publishing** — fail-fast quality at the analytics boundary means
  BI is never served a broken fact.
- **Reviewable modeling** — the star schema is declared as data; a PR shows the
  model change, not imperative joins.
- **Future industries reuse the framework** — a new industry adds a Gold
  manifest, not pipeline code.

## Dependencies

- Silver tables produced by the conforming framework (PR 3).
- Delta Live Tables on Databricks Runtime 14.3 LTS+ (ADR-005).
- Unity Catalog `silver` and `gold` schemas; `DATABRICKS_CATALOG` variable.

## Implementation

- `pipelines/energy/gold_manifest.json` — declarative model specs (kind, source,
  primary key, foreign keys, `date_key`, `aggregate`, expectations).
- `notebooks/shared/gold_manifest.py` — pure-Python validation (kinds,
  aggregations, FK targets, column pinning) plus the `date_dimension_rows`
  calendar generator.
- `notebooks/shared/gold.py` — PySpark helpers: `date_key_expr`, `gold_source`
  (dimension / date-dimension / fact / aggregate-fact branches),
  `_aggregation_expr`, `register_gold`.
- `notebooks/shared/ingest.py` — `apply_expectations` now supports the `fail`
  policy for the Silver-to-Gold boundary.
- `notebooks/gold/transform_energy.py` — the data-driven DLT pipeline notebook.
- `tests/test_gold_manifest.py` — pins the manifest to the Silver manifest and
  generator pack, and unit-tests the date dimension.

Domain-specific analytics (dashboards, BI models, KPI definitions) are
deliberately downstream of this framework and remain the responsibility of each
industry implementation.
