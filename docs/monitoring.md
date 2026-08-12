# Platform Monitoring, Observability & Data Quality

## Overview

Observability combines Databricks System Tables, Lakeflow declarative pipeline event logs, and Azure Log Analytics for operational visibility, cost control, and data reliability. Queries below assume system tables are enabled in the workspace.

---

## 1. Observability Architecture

```text
┌────────────────────────────────────────────────────────┐
│               Azure Databricks Workspace               │
│                                                        │
│  ┌──────────────────┐  ┌────────────────────────────┐  │
│  │Lakeflow Event Log│  │ Databricks System Tables   │  │
│  │ (Data Quality)   │  │ (Audit, Billing, Compute)  │  │
│  └────────┬─────────┘  └─────────────┬──────────────┘  │
└───────────┼──────────────────────────┼─────────────────┘
            │                          │
            ▼                          ▼
┌────────────────────────────────────────────────────────┐
│             Azure Log Analytics Workspace              │
└──────────────────────────┬────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             Alerting & Dashboarding Layer              │
│  - Databricks SQL Executive Dashboards                 │
│  - PagerDuty / Slack / Teams Alerts                    │
└────────────────────────────────────────────────────────┘
```

---

## 2. Databricks System Tables Strategy

Unity Catalog System Tables provide native, SQL-queryable operational logs:

### A. Compute Cost & Usage Monitoring (`system.billing.usage`)
Track DBU consumption by cluster, pipeline, and user:

```sql
SELECT
  usage_date,
  sku_name,
  custom_tags.ResourceClass AS cluster_type,
  SUM(usage_quantity) AS total_dbus,
  SUM(usage_quantity * 0.15) AS estimated_usd_cost
FROM system.billing.usage
WHERE usage_date >= current_date() - INTERVAL 30 DAYS
GROUP BY usage_date, sku_name, custom_tags.ResourceClass
ORDER BY usage_date DESC;
```

### B. Unity Catalog Audit Logs (`system.access.audit`)
Monitor table access, permissions changes, and data export attempts:

```sql
SELECT
  event_time,
  user_identity.email AS user_email,
  action_name,
  request_params.table_full_name AS accessed_table,
  service_name
FROM system.access.audit
WHERE action_name IN ('createTable', 'deleteTable', 'getTable', 'readTable')
  AND event_date >= current_date() - INTERVAL 7 DAYS
ORDER BY event_time DESC;
```

---

## 3. Lakeflow Pipeline Event Log Analysis

Lakeflow writes detailed metrics (records ingested, expectations met/failed, execution duration) directly to an event log table:

```sql
SELECT
  timestamp,
  message,
  details:flow_progress:metrics:num_output_rows AS rows_processed,
  details:flow_progress:data_quality:expectations AS quality_expectations
FROM event_log(TABLE(prod_lakehouse.silver.fact_orders_dlt))
WHERE event_type = 'flow_progress'
ORDER BY timestamp DESC;
```

---

## 4. Data Quality Framework & Expectation Rules

Data quality is enforced deterministically across Medallion layers:

| Layer | Rule Type | Action on Failure | Example Expectation |
| ----- | --------- | ----------------- | ------------------- |
| **Bronze -> Silver** | `EXPECT` | Log & Retain | `EXPECT (customer_id IS NOT NULL)` |
| **Silver** | `EXPECT OR DROP` | Quarantine Row | `EXPECT (email LIKE '%@%') ON VIOLATION DROP ROW` |
| **Gold** | `EXPECT OR FAIL` | Halt Pipeline | `EXPECT (order_amount >= 0) ON VIOLATION FAIL UPDATE` |
