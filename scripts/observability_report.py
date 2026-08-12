"""Run the Milestone A observability query set against a live workspace.

Every query in this report has been executed and validated against the dev
workspace (free account, ``dev_lakehouse`` catalog) via the SQL Statements
API. The report covers the Databricks-native observability surface that needs
no custom framework:

- data-generation job runs, states, and durations (``system.lakeflow.*``),
- table freshness across the medallion layers (UC ``information_schema``),
- representative row volumes (Bronze / Silver / Gold),
- SQL warehouse query health and slowest queries (``system.query.history``),
- cost by day and SKU (``system.billing.usage``),
- operational audit activity (``system.access.audit``).

It shells out to the Databricks CLI (``databricks api post ...``), writing the
statement payload to a temporary JSON file, so it inherits the CLI profile
auth (``.databrickscfg``) and adds no SDK dependency.

Usage::

    python scripts/observability_report.py --profile "An0N Free Acc"

Pipeline update state and the quality expectation events live in the pipeline
event log (``databricks pipelines list-pipeline-events`` /  ``get-update``),
which is not SQL-queryable; the CLI steps are covered in ``docs/monitoring.md``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WAREHOUSE_ID = "83f0bd25083b922e"
DEFAULT_PROFILE = "An0N Free Acc"
MAX_WAIT = "50s"

QUERIES = {
    "JOB RUNS (14d)": """
SELECT
  jr.job_id,
  regexp_replace(j.name, '\\\\[dev .*\\\\] ', '') AS name,
  jr.run_id,
  jr.result_state,
  jr.trigger_type,
  jr.execution_duration_seconds AS duration_s,
  jr.period_start_time
FROM system.lakeflow.job_run_timeline AS jr
LEFT JOIN system.lakeflow.jobs AS j ON jr.job_id = j.job_id
WHERE jr.period_start_time > now() - INTERVAL 14 DAYS
ORDER BY jr.period_start_time DESC
LIMIT 12
""",
    "TABLE FRESHNESS (medallion, newest first)": """
SELECT table_schema, table_name, last_altered
FROM dev_lakehouse.information_schema.tables
WHERE table_schema IN ('bronze', 'silver', 'gold')
  AND table_name NOT LIKE '__materialization%'
ORDER BY last_altered DESC
LIMIT 15
""",
    "DATA VOLUME (representative tables)": """
SELECT 'bronze.weather' AS tbl, count(*) AS rows FROM dev_lakehouse.bronze.weather
UNION ALL SELECT 'bronze.work_orders', count(*) FROM dev_lakehouse.bronze.work_orders
UNION ALL SELECT 'bronze.iot_events', count(*) FROM dev_lakehouse.bronze.iot_events
UNION ALL SELECT 'silver.weather', count(*) FROM dev_lakehouse.silver.weather
UNION ALL SELECT 'silver.customers', count(*) FROM dev_lakehouse.silver.customers
UNION ALL SELECT 'gold.fact_weather_daily', count(*) FROM dev_lakehouse.gold.fact_weather_daily
UNION ALL SELECT 'gold.dim_customer', count(*) FROM dev_lakehouse.gold.dim_customer
""",
    "QUERY HEALTH (warehouse, 14d)": """
SELECT execution_status, count(*) AS n
FROM system.query.history
WHERE start_time > now() - INTERVAL 14 DAYS
GROUP BY 1
ORDER BY n DESC
""",
    "SLOWEST QUERIES (top 5, 14d)": """
SELECT
  execution_status,
  round(total_duration_ms / 1000.0, 1) AS duration_s,
  left(statement_text, 80) AS statement
FROM system.query.history
WHERE start_time > now() - INTERVAL 14 DAYS
ORDER BY total_duration_ms DESC
LIMIT 5
""",
    "COST BY DAY / SKU (14d, quantity-hour units)": """
SELECT date_trunc('DAY', usage_start_time) AS d, sku_name,
       round(sum(usage_quantity), 2) AS qty
FROM system.billing.usage
WHERE usage_start_time > now() - INTERVAL 14 DAYS
GROUP BY 1, 2
ORDER BY 1 DESC, 2
LIMIT 10
""",
    "AUDIT ACTIVITY (7d)": """
SELECT event_date, action_name, count(*) AS n
FROM system.access.audit
WHERE event_date >= current_date() - INTERVAL 7 DAYS
GROUP BY 1, 2
ORDER BY 1 DESC, n DESC
LIMIT 15
""",
}


def find_cli(cli_hint: str | None) -> str:
    """Resolve the ``databricks`` binary from a hint or PATH."""
    if cli_hint:
        return cli_hint
    found = shutil.which("databricks")
    if found:
        return found
    candidates = [
        Path(
            r"C:\Users\gaura\AppData\Local\Microsoft\WinGet\Packages"
            r"\Databricks.DatabricksCLI_Microsoft.Winget.Source_8wekyb3d8bbwe"
            r"\databricks.exe"
        )
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise SystemExit("databricks CLI not found on PATH; pass --cli <path>")


def run_statement(cli: str, profile: str, warehouse_id: str, sql: str) -> tuple[str, list]:
    """Execute ``sql`` via the SQL Statements API; return (state, rows|error)."""
    payload = {
        "warehouse_id": warehouse_id,
        "statement": sql,
        "wait_timeout": MAX_WAIT,
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(payload, handle)
        request_path = handle.name
    command = [
        cli,
        "api",
        "post",
        "/api/2.0/sql/statements",
        "--json",
        f"@{request_path}",
        "-p",
        profile,
        "--output",
        "json",
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=120, check=False
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ["statement exceeded 120s wait"]
    finally:
        Path(request_path).unlink(missing_ok=True)
    if completed.returncode != 0:
        return "CLI_ERROR", [completed.stderr.strip() or completed.stdout.strip()]
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return "PARSE_ERROR", [str(exc), completed.stdout[:500]]
    status = response.get("status", {})
    state = status.get("state", "UNKNOWN")
    if state != "SUCCEEDED":
        return state, [status.get("error", {}).get("message", "unknown error")]
    return state, response.get("result", {}).get("data_array", [])


def render_rows(rows: list) -> str:
    """Pretty-print a rows list of lists with a fixed separator."""
    if not rows:
        return "  (no rows)"
    widths = [0] * len(rows[0])
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))
    lines = []
    for row in rows:
        cells = [str(value).ljust(widths[index]) for index, value in enumerate(row)]
        lines.append("  " + " | ".join(cells).rstrip())
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help="CLI profile name")
    parser.add_argument("--warehouse-id", default=WAREHOUSE_ID, help="SQL warehouse id")
    parser.add_argument("--cli", default=None, help="path to the databricks CLI binary")
    args = parser.parse_args()

    cli = find_cli(args.cli)
    failures = 0
    for section, sql in QUERIES.items():
        print(f"\n=== {section} ===")
        state, rows = run_statement(args.cli or cli, args.profile, args.warehouse_id, sql)
        if state != "SUCCEEDED":
            failures += 1
            print(f"  {state}: {rows[0] if rows else 'no detail'}")
        else:
            print(render_rows(rows))
    print("\nDone: 1 query failed" if failures else "\nDone: all queries succeeded")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
