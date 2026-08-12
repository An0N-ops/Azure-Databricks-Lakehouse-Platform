# Platform Monitoring, Observability & Data Quality

## Overview

Observability on this platform is Databricks-native and verified against the
live dev workspace: **Databricks System Tables** (SQL-queryable) plus the
**Lakeflow pipeline event log** (CLI/API). Every SQL query in this document
was executed successfully against the `dev_lakehouse` catalog on the dev
workspace (SQL warehouse `83f0bd25083b922e`, profile `An0N Free Acc`) and the
output samples shown here are real.

What is **not** yet built (design-only): Azure Log Analytics integration,
PagerDuty/Slack/Teams alerting, and scheduled snapshot dashboards — roadmap
Milestone A follow-ups.

> System Tables must be enabled on the metastore to run the SQL queries;
> enabled schemas observed on the dev workspace: `system.access`, `system.ai`,
> `system.ai_gateway`, `system.alert`, `system.billing`, `system.compute`,
> `system.information_schema`, `system.lakeflow`, `system.mlflow`,
> `system.query`, `system.serving`, `system.storage`.

---

## 1. Quick Start — observability report

The full snapshot is one command (pure Python, shells out to the Databricks
CLI; no SDK dependency):

```powershell
python scripts/observability_report.py --profile "An0N Free Acc"
```

It prints eight sections: job runs (14 d), table freshness, representative
data volumes, warehouse query health, slowest queries, cost by day/SKU, and
operational audit activity. Each section is a standalone query that also
appears below.

Pipeline update state and quality-expectation events are not SQL-queryable;
they live in the pipeline event log (section 4).

---

## 2. Data Generation Job Runs (`system.lakeflow.*`)

`system.lakeflow.jobs` registers job definitions; `system.lakeflow.
job_run_timeline` records each run with its state and duration. Join them to
monitor the `generate_energy_data` job (and any future scheduled jobs):

```sql
SELECT jr.job_id,
       regexp_replace(j.name, '\[dev .*\] ', '') AS name,
       jr.run_id,
       jr.result_state,
       jr.trigger_type,
       jr.execution_duration_seconds AS duration_s,
       jr.period_start_time
FROM system.lakeflow.job_run_timeline AS jr
LEFT JOIN system.lakeflow.jobs AS j ON jr.job_id = j.job_id
WHERE jr.period_start_time > now() - INTERVAL 14 DAYS
ORDER BY jr.period_start_time DESC;
```

Real output (2026-08-12):

```text
1115498002822373 | generate_energy_data | 34722872118317   | SUCCEEDED | ONETIME | 2026-08-10T17:41:15.671Z
1115498002822373 | generate_energy_data | 1004865672170830 | SUCCEEDED | ONETIME | 2026-08-09T15:30:14.574Z
625494808500502  | generate_energy_data | 698632060845729  | ERROR     | ONETIME | 2026-08-05T12:06:59.517Z
```

For the run that failed, `system.lakeflow.job_tasks` /
`system.lakeflow.job_task_run_timeline` carry task-level failure codes.

---

## 3. Medallion Data Health

### A. Table freshness (Unity Catalog `information_schema`)

`last_altered` reflects the most recent delta commit to each table — the
backbone of a freshness contract (alert when `bronze.weather` stops moving):

```sql
SELECT table_schema, table_name, last_altered
FROM dev_lakehouse.information_schema.tables
WHERE table_schema IN ('bronze', 'silver', 'gold')
  AND table_name NOT LIKE '__materialization%'
ORDER BY last_altered DESC
LIMIT 15;
```

Real output (2026-08-12, newest at top — the 2026-08-10 pipeline run):

```text
bronze | event_log_96f70965_...   | 2026-08-10T17:45:06.085Z
gold   | fact_sensor_daily        | 2026-08-10T17:45:03.818Z
gold   | dim_date                 | 2026-08-10T17:44:05.613Z
silver | asset_types              | 2026-08-10T17:43:27.885Z
...
```

> The DLT event-log backing table (`bronze.event_log_<pipeline_id>`) also
> lives in the medallion schema; that is expected, not a product table.

### B. Data volume (representative counts)

```sql
SELECT 'bronze.weather' AS tbl, count(*) AS rows FROM dev_lakehouse.bronze.weather
UNION ALL SELECT 'bronze.work_orders', count(*) FROM dev_lakehouse.bronze.work_orders
UNION ALL SELECT 'bronze.iot_events',  count(*) FROM dev_lakehouse.bronze.iot_events
UNION ALL SELECT 'silver.weather',     count(*) FROM dev_lakehouse.silver.weather
UNION ALL SELECT 'silver.customers',   count(*) FROM dev_lakehouse.silver.customers
UNION ALL SELECT 'gold.fact_weather_daily', count(*) FROM dev_lakehouse.gold.fact_weather_daily
UNION ALL SELECT 'gold.dim_customer',  count(*) FROM dev_lakehouse.gold.dim_customer;
```

Real output (2026-08-12):

```text
bronze.weather  | 584000
bronze.iot_events | 1200000
bronze.work_orders | 48000
silver.weather  | 146000
silver.customers | 250
gold.fact_weather_daily | 146000
gold.dim_customer | 250
```

---

## 4. Warehouse Query Health (`system.query.history`)

Every statement executed on SQL warehouses, with execution status, duration,
and bytes read. Useful for regression detection (e.g. a pipeline that
suddenly reads far more files per micro-batch):

```sql
-- error-rate snapshot
SELECT execution_status, count(*) AS n
FROM system.query.history
WHERE start_time > now() - INTERVAL 14 DAYS
GROUP BY 1 ORDER BY n DESC;

-- slowest statements
SELECT execution_status,
       round(total_duration_ms / 1000.0, 1) AS duration_s,
       left(statement_text, 80) AS statement
FROM system.query.history
WHERE start_time > now() - INTERVAL 14 DAYS
ORDER BY total_duration_ms DESC LIMIT 5;
```

Real output (2026-08-12): `FINISHED 1412`, `FAILED 104`, `CANCELED 1`;
slowest are `SHOW TABLES` refreshes and `REFRESH STREAMING TABLE` statements
(247.8 s, 109.2 s, 58.8 s, 34.4 s, 32.9 s).

---

## 5. Cost by Day and SKU (`system.billing.usage`)

Attribution is available per object via the `usage_metadata` struct
(`dlt_pipeline_id`, `job_id`, `warehouse_id`); quantities are DBU-hour units,
not USD:

```sql
SELECT date_trunc('DAY', usage_start_time) AS d,
       sku_name,
       round(sum(usage_quantity), 2) AS qty
FROM system.billing.usage
WHERE usage_start_time > now() - INTERVAL 14 DAYS
GROUP BY 1, 2 ORDER BY 1 DESC, 2 LIMIT 10;
```

Real output (2026-08-12, top 5): on 2026-08-10 —
`PREMIUM_JOBS_SERVERLESS_COMPUTE_US_EAST_OHIO 2.03`,
`PREMIUM_SERVERLESS_SQL_COMPUTE_US_EAST_OHIO 1.47`,
`PREMIUM_DATABRICKS_STORAGE_US_EAST_OHIO 2.47` (the day the generator job and
the full medallion update ran); on 2026-08-11 the workspace was idle
(storage only, 0.11).

---

## 6. Operational Audit (`system.access.audit`)

Lightweight activity roll-up (login method, object lifecycle, access):

```sql
SELECT event_date, action_name, count(*) AS n
FROM system.access.audit
WHERE event_date >= current_date() - INTERVAL 7 DAYS
GROUP BY 1, 2 ORDER BY 1 DESC, n DESC LIMIT 15;
```

Real output (2026-08-12): `deletePipeline 4` (teardown activity), `tokenLogin
254` (the CLI/automation login path), `generateTemporaryTableCredential 56`,
`updateTables 14` (the medallion update commits). For full detail join the
`user_identity`/`request_params` structs and filter by `action_name`.

---

## 7. Pipeline Updates & Quality Events (pipeline event log)

Pipeline update runs, per-flow quality metrics, and failure detail are **not**
in System Tables — they come from the pipeline's event log:

```powershell
# recent pipeline events (update started/completed/failed, quality events)
databricks pipelines list-pipeline-events <PIPELINE_ID> --max-results 20 -o json -p "<profile>"

# full detail of a single update (flow state, row counts, expectation results)
databricks pipelines get-update <PIPELINE_ID> <UPDATE_ID> -p "<profile>"
```

On the dev workspace the latest pipeline is `96f70965-aabf-40a7-949c-a60a05797cc9`.
The event log is also readable as a Delta table (fully qualified):
`dev_lakehouse.bronze.event_log_96f70965_aabf_40a7_949c_a60a05797cc9`
(unqualified names resolve through a search path that may not include the
catalog, so always qualify).

The observability report's Job Runs section covers the generator job; run the
CLI commands above for the medallion pipeline itself.

---

## 8. Data Quality Framework (boundary policies, ADR-005)

Quality expectations are declared per table in the layer manifests and
mapped to Lakeflow decorators (`notebooks/shared/ingest.py`,
`apply_expectations`):

| Boundary | Policy | Decorator | Failure behavior |
| -------- | ------ | --------- | ---------------- |
| Bronze → Silver | **retain** | `dp.expect` | violating rows preserved in bronze; violation recorded in the pipeline event log |
| Silver conformed | **drop** (where declared) | `dp.expect_or_drop` | violating row quarantined (omitted from the target) |
| Silver → Gold | **fail** | `dp.expect_or_fail` | update aborted; no broken analytics table published |

Examples from the manifests: `weather` enforces non-null `weather_id` /
valid `station_id` at the retain boundary; gold facts enforce positive
measures (`usage_mwh >= 0`) with the fail policy. Violating rows and
pass/fail counts are visible per update in the pipeline event log (§7).

---

## 9. Roadmap for this section (Milestone A leftovers)

- Scheduled snapshot: run `observability_report.py` as a bundle job and
  publish the snapshot to a `metrics` schema table.
- Alerts: Databricks-native — SQL alert on the freshness query, job success/
  failure webhooks, `system.alert` for warehouse health anomalies.
- Azure Log Analytics export of `system.*` tables via diagnostic settings;
  PagerDuty/Slack/Teams routing (design-only today).