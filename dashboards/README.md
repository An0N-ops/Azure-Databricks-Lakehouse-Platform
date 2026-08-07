# Enterprise Dashboards & Visualization Definitions

This directory documents Databricks AI/BI (Lakeview) dashboards and Power BI
dataset models for Phase 4 reporting. Dashboard **definitions are code**: the
serialized `lvdash.json` specs and bundle resource configs live under
[`bundle/src/`](../bundle/src) and [`bundle/resources/`](../bundle/resources),
deployed as part of the **Databricks Asset Bundle** (see
[`bundle/databricks.yml`](../bundle/databricks.yml)), not via ad-hoc CLI calls.

## Phase 4 — Live Dashboards

### NorthGrid Energy Operations (`bundle/resources/energy_operations.dashboard.yml`)
Databricks AI/BI dashboard deployed on top of the Gold star schema
(`fact_work_order`, `fact_maintenance_event`, `fact_sensor_daily` joined to
`dim_*`). The JSON spec lives at `bundle/src/energy_operations.lvdash.json` and
the queries use bare table names resolved per environment through the bundle's
`datasets_catalog` / `dataset_schema` variables.

- **KPIs**: Open work orders, maintenance cost, downtime hours, sensor alerts.
- **Charts**: Work orders by month & status, sensor alerts by region,
  maintenance cost by root cause, work order detail table.
- **Filters**: Global date range (work orders / maintenance / sensor dates) and
  region multi-select.

## Deploying dashboards (Databricks bundle)

Dashboards are a `resources.dashboards` entry in the bundle and deploy alongside
the pipelines/jobs with `databricks bundle deploy`. The very first deploy can
adopt an existing dashboard (see **Binding** below); afterwards `bundle deploy`
updates the same dashboard in place.

```bash
# From the bundle/ directory:
databricks bundle validate --target dev
databricks bundle deploy --target dev
```

Environment-specific values are parameterized:

| Bundle variable | Purpose | Default |
| --------------- | ------- | ------- |
| `catalog`       | Unity Catalog catalog (e.g. `dev_lakehouse`) | `dev_lakehouse` |
| `gold_schema`   | Schema holding the Gold reporting tables | `gold` |
| `warehouse_id`  | Serverless SQL warehouse executing dashboard queries | set per target |

### Binding an existing dashboard

To take over a dashboard that was created outside the bundle (e.g. via
`databricks lakeview create`) and make the bundle the source of truth for it:

```bash
databricks bundle generate dashboard --existing-id <DASHBOARD_ID> \
  --profile "An0N Free Acc"
databricks bundle deployment bind <resource-key> <DASHBOARD_ID> \
  --target dev --profile "An0N Free Acc" --auto-approve
```

Set `parent_path` in the dashboard resource to the folder where the remote
dashboard lives so `bundle deploy` updates it instead of recreating it with a
new ID. After binding, `bundle deploy` does not prompt and keeps the same
dashboard ID.

## Included Dashboard Definitions (planned / future)
- **Executive Financial KPI Dashboard**: Monthly revenue, gross margins, and Oracle ERP ledger reconciliation.
- **Customer 360 & Lifetime Value**: Customer segmentation, churn risk scores, and purchasing trends.
- **Platform Operations & DLT Health**: Pipeline execution latency, data quality error rates, and DBU cost breakdown.

## Generating/editing a dashboard spec

The canonical workflow is: edit the spec in the UI, sync it back into the bundle,
commit, and deploy:

```bash
databricks bundle generate dashboard --resource energy_operations \
  --profile "An0N Free Acc" --force
```

This overwrites `bundle/src/energy_operations.lvdash.json` with the current
workspace definition. Then review, commit, and `databricks bundle deploy`.

> Windows PowerShell note: the Databricks CLI mangles multi-line JSON arguments
> when invoked with `&`. The `bundle`/`generate` commands above do not pass the
> dashboard payload through the shell, so they are safe to run from PowerShell.

## References

- Databricks docs: [Dashboards in a bundle](https://docs.databricks.com/dev-tools/bundles/resources.html#dashboard)
- Databricks docs: [`databricks bundle generate dashboard`](https://docs.databricks.com/dev-tools/cli/bundle-commands.html#generate)