# Demo & Evidence

This directory holds the artifact structure for demonstrating that the
platform **actually works end-to-end**: synthetic data in, schema-conformed
Silver and Gold out, deployed from Databricks Asset Bundles, and consumed by a
live AI/BI dashboard.

- **[`runbook.md`](runbook.md)** — the reproducible, step-by-step flow a
  technical reviewer follows to see the platform working (or to reproduce it
  themselves).
- **[`screenshots/`](screenshots/)** — placeholder for real evidence captures.

## Evidence checklist

Screenshots are intentionally **not** committed: they must be captured from a
real run against a live workspace and are the responsibility of whoever runs
the demo. Each file below documents one checkpoint of the runbook.

| File | Demonstrates | Where it comes from | What a reviewer should look for |
| ---- | ------------ | ------------------- | ------------------------------- |
| `01-platform-architecture.png` | Overall system design | [`architecture/exports/platform-architecture.svg`](../../architecture/exports/platform-architecture.svg) | Medallion zones, Unity Catalog governance, source systems, consumers |
| `02-data-generation.png` | Deterministic synthetic data | Generator CLI or `generate_energy_data` job output (`manifest.json`, entity counts) | Same seed reproduces identical row counts; a `manifest.json` is produced |
| `03-bundle-validation.png` | Bundle is valid | `databricks bundle validate --target dev --strict` output | No errors, resolved `dev` target |
| `04-bundle-deployment.png` | Bundle deploys to the workspace | `databricks bundle deploy --target dev` output | DLT pipeline + job + dashboard resources deployed |
| `05-pipeline-run.png` | DLT pipeline executes | Workspace pipeline UI or `databricks pipelines get-update` | Update reaches `COMPLETED`; all tables materialized |
| `06-bronze-silver-gold.png` | Data flows through every layer | Row-count queries per schema (runbook step 6) | Bronze ≥ Silver ≥ Gold row counts; SCD2 history rows on `silver.customers` |
| `07-data-quality.png` | Quality expectations are live | Pipeline **Events** tab search for expectation events | Expectations are listed; violations (if any) are flagged, not silent |
| `08-dashboard.png` | Analytics on top of Gold | AI/BI workspace dashboard *NorthGrid Energy Operations* | Charts render from Gold tables; filters/date dimension work |

## Rules

1. Capture from a **real** run — never staged or doctored images.
2. If the demo is re-run with different data, recapture affected screenshots.
3. Keep the filenames above; the runbook references them.