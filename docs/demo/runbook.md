# Demonstration Runbook

"How can a technical reviewer see this platform working?"

Eight steps, from deterministic synthetic data to a live dashboard on Gold.
Every command below is real and runnable from a clone of this repository.
Screenshots at each checkpoint go into [`screenshots/`](screenshots/) per the
[evidence checklist](README.md).

## Prerequisites

- A Databricks workspace with the Databricks CLI authenticated
  (`databricks auth login`, or an active `~/.databrickscfg` profile).
- A local override `bundle/databricks.local.yml` pointing `dev` at that
  workspace (host, `catalog`, `landing_path`, `warehouse_id`). This file is
  intentionally not committed; `bundle/databricks.local.yml.example` style
  overrides are consumed by the bundle automatically.
- Python 3.11 with `pytest` and `ruff` installed.

Use `-p <profile>` on databricks commands to select the workspace profile.

## 1. Generate synthetic data

Workspace (this is how the demo data is produced for the live pipeline):

```bash
databricks jobs list -p <profile>            # find "generate_energy_data"
databricks jobs run-now <JOB_ID> -p <profile>
```

Locally (same generator, full determinism):

```bash
PYTHONPATH=sample-data python -m sample_data generate --industry energy --seed 42 --scale 0.05
```

Checkpoint: a `manifest.json` is written next to the landing files with
entity counts, seed, and window; re-running with the same seed reproduces
identical output.

## 2. Validate the project

```bash
pytest            # 138 tests: manifests, generator, SCD2 semantics
ruff check .
ruff format --check .
```

## 3. Validate the Databricks Asset Bundle

```bash
python scripts/validate_bundle.py --bundle .        # offline structural validation
cd bundle
databricks bundle validate --target dev --strict -p <profile>
```

Checkpoint: `Validation OK` with the resolved `dev` target.

## 4. Deploy the bundle

```bash
cd bundle
databricks bundle deploy --target dev --auto-approve -p <profile>
```

Deploys the `energy_lakehouse` Lakeflow pipeline, the `generate_energy_data` job,
and the `energy_operations` AI/BI dashboard (all declared in
`bundle/databricks.yml` and `bundle/resources/*.yml`).

## 5. Run the pipeline

```bash
databricks pipelines list-pipelines -p <profile>    # find "energy_lakehouse"
databricks pipelines start-update <PIPELINE_ID> --cause API_CALL -p <profile>
databricks pipelines get-update <PIPELINE_ID> <UPDATE_ID> -p <profile>
```

Repeat `get-update` until the state is `COMPLETED`. On the first run after an
SCD2 change, the pipeline recreates the `silver.customers` and `silver.assets`
streaming tables — a "recreated" event is expected, not a failure.

## 6. Verify Bronze, Silver, and Gold

List tables per layer:

```bash
databricks tables list dev_lakehouse bronze --omit-columns -p <profile>
databricks tables list dev_lakehouse silver --omit-columns -p <profile>
databricks tables list dev_lakehouse gold --omit-columns -p <profile>
```

Count rows through the SQL warehouse (repeat per schema; values are
deterministic for seed 42, record them here for the evidence docs):

```bash
databricks api post /api/2.0/sql/statements --json '{
  "warehouse_id": "83f0bd25083b922e",
  "catalog": "dev_lakehouse",
  "schema": "silver",
  "statement": "SELECT COUNT(*) AS n FROM customers"
}' -p <profile>
```

Checkpoints: every Bronze entity has a table; Silver dedupes (weather is
ingested as 3 batches but conforms to one row per observation); Gold exposes
9 dimensions + `dim_date` + 4 facts that join via `date_key`/foreign keys.

**SCD2 check (customers/assets):**

```bash
databricks api post /api/2.0/sql/statements --json '{
  "warehouse_id": "83f0bd25083b922e",
  "catalog": "dev_lakehouse",
  "schema": "silver",
  "statement": "SELECT customer_id, account_status, credit_rating, __START_AT, __END_AT FROM customers ORDER BY customer_id LIMIT 20"
}' -p <profile>
```

- After the first run: exactly **one version per key**, `__END_AT` unset
  (current flag), no drift.
- Re-run the generator with the **same seed** and the pipeline again:
  identical tracked attributes produce **no new versions** (SCD2 absorbs
  repeated records instead of growing history).
- Optional controlled change: write a new batch
  `{landing}/energy/customers/batch_date=<today>/customers.csv` copying one
  real customer row but with `account_status` changed, re-run the pipeline,
  and the SCD2 table closes the old version (`__END_AT` set) and opens a new
  one. This is the tracked-attribute behavior on demand.

## 7. Verify data quality expectations

Open the pipeline in the Databricks workspace UI → **Events** tab → search
`expectation`. The Bronze-to-Silver boundary uses the retain policy: rows are
kept and violations appear as expectation events (never silently dropped);
Gold uses the fail policy for its contracts. Optionally:

```bash
databricks pipelines list-pipeline-events <PIPELINE_ID> --max-results 50 -p <profile>
```

## 8. Open the dashboard

Workspace → **Dashboards** (AI/BI) → **NorthGrid Energy Operations** (created
by the bundle at `/Users/<you>/dashboards`). Charts query the Gold star
schema of `dev_lakehouse`; facts join dimensions via `date_key`, so date
filters and per-dimension breakdowns should work across charts.

---

You are done: this is the platform, seen working end-to-end with no manual
intervention between data and dashboard.