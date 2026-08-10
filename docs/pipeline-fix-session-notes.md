# Pipeline Fix Session Notes — LSDP Migration (RESOLVED, next session 2026-08-10)

> **When to read this**: You are resuming work on the `energy_lakehouse` DLT/Lakeflow
> pipeline (`[dev gauravsahu06904] energy_lakehouse`). This file is the detailed handoff
> so you can pick up exactly where the session stopped. **Read the whole file.**

---

## 1. TL;DR — Where We Are Right Now

- The pipeline was **fully migrated from legacy `dlt` (Delta Live Tables) syntax to the
  modern Lakeflow Spark Declarative Pipelines (LSDP) `dp` API** (`from pyspark import
  pipelines as dp`) in **6 source files** (see §4).
- `138` pytest tests pass; `bundle deploy` to the `dev` target **succeeded** (deployed
  bundle `lakehouse`, workspace of profile `"An0N Free Acc"`).
- **All 28 conflicting UC tables were dropped** BEFORE the re-run: 14 gold
  `MATERIALIZED_VIEW` tables (older MV design) + 14 stale `silver.silver_source_*`
  prep tables (old materialized-prep design; prep is now a temp view).
- **✅ RESOLVED (2026-08-10)**: the full-refresh update `77502e28-0f8c-4861-8245-aeeb4c504f52`
  FAILED with `DLTAnalysisException: Please rename the following system reserved columns
  in your source: __START_AT,__END_AT` on the two flows whose Silver source is SCD2
  (`gold.dim_customer`, `gold.dim_asset`). Fix: `notebooks/shared/gold.py` →
  `gold_stream_source()` now `.drop("__END_AT", "__START_AT")` after the SCD2
  expiry filter (the AUTO CDC flow rejects reserved SCD2 column names in its source).
  Redeployed, re-ran full refresh **update `bb96e33a-22bf-4d5f-b0cd-80085ff2f67a` →
  COMPLETED**. All 14 gold tables exist: 12 STREAMING_TABLE + `dim_date` /
  `fact_sensor_daily` as MATERIALIZED_VIEW. Row counts: `gold.dim_customer`=250,
  `gold.dim_asset`=2500, `silver.customers`=250, `dim_date`=943, `fact_sensor_daily`=295,916.
  **The code changes are still uncommitted on `feat/silver-scd2` (user manages PRs).**
- Pipeline's last known good state before this migration: COMPLETED with gold as
  materialized views — that design was **rejected by the user** ("Nope MVs won't work.
  We need streaming tables on silver/gold layers"), hence this migration.

---

## 2. Environment Facts (IMPORTANT — do not guess)

| Item | Value |
|---|---|
| Pipeline id | `96f70965-aabf-40a7-949c-a60a05797cc9` |
| Pipeline name | `[dev gauravsahu06904] energy_lakehouse` (deployed via bundle, serverless, `continuous: false`) |
| in-flight update | `77502e28-0f8c-4861-8245-aeeb4c504f52` (full refresh, started last session) |
| CLI profile | `"An0N Free Acc"` (NOT `dev`) — host `https://dbc-a12d554d-e06c.cloud.databricks.com` (AWS) |
| CLI executable | `C:\Users\gaura\AppData\Local\Microsoft\WinGet\Packages\Databricks.DatabricksCLI_Microsoft.Winget.Source_8wekyb3d8bbwe\databricks.exe` |
| Bundle root | `C:\Users\gaura\Desktop\Azure-Databricks-Lakehouse-Platform\bundle\databricks.yml` (run bundle commands with `workdir` = that `bundle\` dir) |
| Deployed bundle | name `lakehouse`, target `dev` |
| Catalog/schemas | `dev_lakehouse.bronze` / `dev_lakehouse.silver` / `dev_lakehouse.gold` |
| Local Python | use `.venv\Scripts\python.exe -m pytest tests -q` (no global pytest) |
| Repo root | `C:\Users\gaura\Desktop\Azure-Databricks-Lakehouse-Platform` |
| Skill docs (authoritative API) | `C:\Users\gaura\.config\opencode\skills\databricks-pipelines\references\*.md` (auto-cdc-python.md, temporary-view-python.md, streaming-table-python.md, materialized-view-python.md, expectations-python.md, dlt-migration.md, python-basics.md) |

---

## 3. Background / Problem History (why we are here)

1. The energy Lakehouse DLT pipeline kept failing across several full-refresh cycles.
   Diagnosed fixes in order:
   - Removed unsupported `ignore_null_keys` kwarg (silver `apply_changes` calls).
   - `track_by` → `track_history_column_list` (new API name, Python has no `track_by`).
   - Gold prep **streaming** reads of silver blew up with `DELTA_SOURCE_TABLE_IGNORE_CHANGES`
     (MERGE at source version ~3): the change-feed read (`readChangeFeed=true`) was not
     honored in the legacy `dlt.table` path — the execution plan showed a plain
     `DeltaSource` with `__DeleteVersion/__UpsertVersion` tracking columns and no
     `_change_type` column.
2. **Workaround (completed, then rejected)**: gold was rebuilt entirely as
   `@dlt.table` **materialized views** over batch reads. Pipeline COMPLETED; 14 gold
   tables existed as `MATERIALIZED_VIEW`. User then rejected this: "Nope MVs won't
   work. We need streaming tables on silver/gold layers... MAKE SURE to check the
   documentation of databricks LSDP pipelines to use latest functions."
3. **This session**: read the LSDP skill docs (§5 key facts), migrated ALL layers to the
   `dp` API, dropped the conflicting tables, and kicked off a full refresh (in flight).

---

## 4. Code Changes Made This Session (all uncommitted)

`git status --short` (all modified, NOT committed):

```
 M notebooks/bronze/ingest_energy.py
 M notebooks/shared/gold.py
 M notebooks/shared/ingest.py
 M notebooks/shared/scd2.py
 M notebooks/shared/silver.py
 M notebooks/silver/transform_energy.py
```

### 4.1 `notebooks/shared/ingest.py` (bronze)
- `apply_expectations()`: `import dlt` → `from pyspark import pipelines as dp`;
  decorators `dlt.expect_or_drop/expect/expect_or_fail` → `dp.expect_or_drop` /
  `dp.expect` (retain) / `dp.expect_or_fail`. Docstring: "DLT" → "Lakeflow".
- `dlt_bronze_table()` renamed to **`dp_bronze_table()`**: registers via `dp.table(
  name=..., comment=..., table_properties={"delta.enableChangeDataFeed": "true"})`
  around the Auto Loader streaming function (streaming DataFrame ⇒ streaming table).
  Kept `CDF_PROPERTY`, `_default_commit_id`, `with_audit_columns`, `bronze_stream`,
  `autoloader_reader` unchanged.
- **CALLER UPDATED**: `notebooks/bronze/ingest_energy.py` now calls `ingest.dp_bronze_table(...)`.

### 4.2 `notebooks/shared/silver.py`
- Module docstring and comments updated to LSDP wording.
- `register_silver()` now:
  1. Prep = **`@dp.temporary_view(name=f"silver_source_{name}")`** (UNQUALIFIED name —
     schema-qualified `silver.silver_source_x` no longer used; those old UC tables were
     dropped) returning the conformed bronze **stream**, with expectations via
     `apply_expectations(..., on_violation="retain")` (i.e. `dp.expect`).
  2. `dp.create_streaming_table(name="silver.<name>", comment=..., table_properties={
     "delta.enableChangeDataFeed": "true"})` — the empty CDC target.
  3. SCD1: `dp.create_auto_cdc_flow(target=..., source=prep_name, keys=list(spec["keys"]),
     sequence_by="_ingested_at", stored_as_scd_type="1")`.
  4. SCD2: same but `stored_as_scd_type=2` + `track_history_column_list=list(spec["track_by"])`.
- `conformed_bronze()` unchanged (streams bronze via `spark.readStream.table`).

### 4.3 `notebooks/shared/gold.py` (biggest rework)
- **Streaming path for dimensions + non-aggregate facts** (12 of 14 gold tables):
  `gold_stream_source(spark, spec, ...)` reads the silver source change feed:
  ```python
  spark.readStream.format("delta")
      .option("readChangeFeed", "true")
      .table(gold_manifest.resolve_source_table(spec, variables))
      .filter(F.col("_change_type") != "update_preimage")
  # plus, ONLY when "__END_AT" in df.columns (SCD2 sources like customers/assets):
  #   filter out update_postimage rows whose __END_AT IS NOT NULL (expired versions)
  ```
  then adds `date_key` for facts. Registered via:
  `@dp.temporary_view(name=f"gold_source_{name}")` (expectations fail policy) →
  `dp.create_streaming_table(name="gold.<name>", table_properties=CDF)` →
  ```python
  dp.create_auto_cdc_flow(
      target=target_name, source=prep_name,
      keys=_gold_keys(spec),            # primary_key normalized to list
      sequence_by="_commit_timestamp",
      stored_as_scd_type="1",
      apply_as_deletes=F.expr("_change_type = 'delete'"),
      except_column_list=["_change_type", "_commit_version", "_commit_timestamp"],
  )
  ```
  Rationale (documented in module docstring): silver is MERGE-written; a plain stream
  dies with `DELTA_SOURCE_TABLE_IGNORE_CHANGES`; CDF read + AUTO CDC flow is the
  documented propagation pattern. The `__END_AT`-expiry filter removes the ambiguous
  expire-vs-insert pair in one SCD2 commit so the last applied row per key is
  deterministic (the newest version's insert).
- **Materialized-view path (2 of 14 gold tables)** — kept intentionally:
  - `dim_date` (`kind=date_dimension`, generated rows, no silver source),
  - `fact_sensor_daily` (`aggregate` spec — running streaming aggregation can't
    retract superseded readings; MV recomputes from source state, per docs).
  Both via `@dp.materialized_view(name=..., comment=..., table_properties=CHANGE_DATA_FEED)`
  over the existing **batch** `gold_source()`. Fail-policy expectations via
  `apply_expectations(..., on_violation="fail")`.
- Helpers: `_gold_keys()`, `_register_streaming()`, `_register_materialized()`.
- Old MV-era `register_gold()` (was using `import dlt` / `dlt.table`) **deleted**
  (removed the duplicate; the new `register_gold()` branches on the two paths).
- NOTE: `_register_streaming`/`register_gold` no longer pass `target_schema` into the
  streaming helper (signature dropped) — don't reintroduce it.

### 4.4 `notebooks/shared/scd2.py` + `notebooks/silver/transform_energy.py`
- Docstrings only: `dlt.apply_changes` → `dp.create_auto_cdc_flow`,
  `track_by` → `track_history_column_list`, "DLT" → "Lakeflow".

### 4.5 Files intentionally NOT changed
- `notebooks/shared/bronze_manifest.py`, `silver_manifest.py`, `gold_manifest.py`
  (pure-Python manifests/validation — no Spark/DLT imports).
- `bundle/databricks.yml` (pipeline config fine: `serverless: true` ⇒ AUTO CDC etc.
  supported; channel CURRENT). `bundle/resources/energy_operations.dashboard.yml`.
- `notebooks/shared/` tests are pure-Python manifest/scd2 tests — untouched, all pass.

---

## 5. LSDP API Facts Verified From Skill Docs (the ground truth)

Source: `databricks-pipelines` skill `references/` (already loaded into context).

- **Import**: `from pyspark import pipelines as dp` (legacy aliases like
  `dp.apply_changes` still parse but must be migrated).
- **Decorators**: `@dp.table()` (streaming DF ⇒ streaming table; batch DF ⇒ MV,
  prefer explicit `@dp.materialized_view()`), `@dp.temporary_view(name=, comment=)`
  (pipeline-scoped, NOT materialized, either batch or streaming), `@dp.materialized_view()`.
- **Expectations** stack on ALL three decorators; `@dp.expect` (warn/retain),
  `@dp.expect_or_drop`, `@dp.expect_or_fail`, plus `expect_all*` dicts
  (`dp.create_streaming_table` also accepts `expect_all_or_fail={...}` directly).
- **CDC**: `dp.create_auto_cdc_flow(target=, source=<string table/view name — never a
  DataFrame>, keys=, sequence_by=, stored_as_scd_type=1|2, apply_as_deletes=<expr or
  string>, apply_as_truncates=, ignore_null_updates=, column_list=, except_column_list=,
  track_history_column_list=, track_history_except_column_list=, name=, once=)`.
  - `stored_as_scd_type`: **integer `2` for Type 2, string `"1"` for Type 1** (don't quote 2).
  - `sequence_by` accepts a string col name, `col("ts")`, or `struct("ts","id")`.
  - Does NOT return a value — call at top level. Target must be pre-created with
    `dp.create_streaming_table()`.
  - SCD2 targets get `__START_AT`/`__END_AT` columns. (Confirmed in the live UC schema
    of old silver SCD2 tables, e.g. `silver.weather` properties show
    `apply_changes.scd_type: TYPE1` etc.)
- **temp-view patterns**: `@dp.temporary_view()` returning `spark.readStream.table(...)`
  is the documented pre-filter feeding a CDC flow ("don't materialize a streaming
  table just for filtering"); downstream `spark.readStream.table("view")`.
- **skipChangeCommits**: set on `spark.readStream.option("skipChangeCommits","true")`
  when a stream reads an upstream table with update/delete commits AND you want to
  IGNORE those changes (not our gold case — gold must propagate them, hence CDF).
- **`dp.create_streaming_table(name=...)`**: "Same parameters as `@dp.table()` except
  `private`, plus the three `expect_all*` dicts."
- **Serverless pipeline** (ours) supports all of the above; MV incremental refresh
  needs serverless + row tracking, falls back to full recompute (fine).

---

## 6. Commands / What Actually Ran Last Session (with results)

```powershell
# \venv tests + compile
.venv\Scripts\python.exe -m pytest tests -q            # => 138 passed in 2.53s
.venv\Scripts\python.exe -m py_compile <6 changed .py files>   # => OK

# deploy (profile "An0N Free Acc", workdir bundle)
& "...\databricks.exe" bundle deploy -t dev -p "An0N Free Acc" --auto-approve
# => "Deployment complete!" (stderr noise is normal PowerShell wrapper behavior)

# list gold/silver tables (note: 2>$null on get swallows errors — avoid for diagnostics)
& "...\databricks.exe" api get "/api/2.1/unity-catalog/tables?catalog_name=dev_lakehouse&schema_name=gold" -p "An0N Free Acc"

# drop conflicting tables (all 28 reported "dropped ..." — confirmed OK)
& "...\databricks.exe" api delete "/api/2.1/unity-catalog/tables/dev_lakehouse.gold.<table>" -p "An0N Free Acc"   # x14
& "...\databricks.exe" api delete "/api/2.1/unity-catalog/tables/dev_lakehouse.silver.silver_source_<entity>" -p "An0N Free Acc"  # x14

# start full refresh
# => {"update_id": "77502e28-0f8c-4861-8245-aeeb4c504f52"}

# poll loop that RETURNED EMPTY STATE (needs fixing when resuming):
for (...) { & ... pipelines get-update 96f70965-aabf-40a7-949c-a60a05797cc9 77502e28-0f8c-4861-8245-aeeb4c504f52 -p "An0N Free Acc" 2>$null ... ; $u.state }
# printed "state=" (blank) for 18 x 20s — do NOT trust; re-run without 2>$null
```

---

## 7. Data / Object State (what exists in UC right now)

- **bronze**: 13 Auto Loader streaming tables (with CDF property) — untouched this
  session; also `silver.inventory` target + `intended`-style entities exist (silver has
  an `inventory` SCD entity with no gold dim — expected).
- **silver**: 13 (or 14, incl. inventory) SCD streaming targets intact from prior runs
  (they keep `apply_changes` feature flags in table props; LSDP AUTO CDC should
  re-bind to the same tables — if the engine rejects a flow-type change in place,
  next resort: drop ALL 14 silver targets and let the refresh recreate them).
- **silver**: `silver_source_*` (14) — **dropped** (were obsolete materialized preps).
- **gold**: seed `escrow`? NOTE — gold schema currently has **no tables** (all 14
  dropped: `dim_region, dim_asset_type, dim_work_order_status, dim_employee_role,
  dim_part_type, dim_customer, dim_location, dim_asset, dim_employee, dim_date,
  fact_work_order, fact_maintenance_event, fact_sensor_daily, fact_weather_daily`).
  The refresh will recreate 12 streaming + 2 MVs (`dim_date`, `fact_sensor_daily`).
- **in-flight update** `77502e28-0f8c-4861-8245-aeeb4c504f52` **FAILED (resolved)**;
  successful rebuild = update `bb96e33a-22bf-4d5f-b0cd-80085ff2f67a` (COMPLETED 2026-08-10).

---

## 8. Next Steps (checklist — resume here)

1. ✅ **DONE (2026-08-10)**: update `77502e28` FAILED → diagnosed via
   `list-pipeline-events` (reserved `__START_AT`/`__END_AT` columns in `gold_stream_source`
   SCD2 temp views) → fixed in `gold.py` (drop the 2 reserved columns after the
   `__END_AT` expiry filter) → redeploy + full refresh `bb96e33a` **COMPLETED**.
   Verified: 12 gold STREAMING_TABLE + 2 MV, SCD2 dims populated (dim_customer=250,
   dim_asset=2500).
2. **To do**: commit the 6 modified files + this notes file (not yet committed; follow
   repo commit style — check `git log --oneline -10`). Possibly also refresh
   `docs/*.md` references to `dlt.`/`apply_changes` if any remain
   (`Get-ChildItem -Recurse docs | Select-String "dlt\.|apply_changes"`).
3. Remaining from old checklist (kept for reference, superseded by the fix above):
   - If a future run ever re-fails on `DELTA_SOURCE_TABLE_IGNORE_CHANGES` after a
     data regeneration, note that gold reads silver via CDF and silver `_source`
     temp views read bronze append streams — generator changes are NOT needed;
     the declared design already propagates MERGEs via CDF. (Fallback only if the
     engine ever rejects a flow-type change: drop the affected UC table and
     full-refresh.)

## 9. Gotchas / lessons (self-notes for next time)

- Profile is `"An0N Free Acc"`, never `dev`; always pass `-p` explicitly.
- `bundle deploy` must run with `workdir = bundle\` (bundle root), else it fails.
- PowerShell `2>$null` on `databricks api get` hides both noise AND errors — for
  debugging, capture stderr.
- Pipeline-managed tables can be dropped via `api delete /api/2.1/unity-catalog/tables/<full_name>`
  (used repeatedly; works with this free workspace + owner account).
- Table dataset types cannot change in place (`CANNOT_CHANGE_DATASET_TYPE`) — always
  drop before changing STREAMING_TABLE ↔ MATERIALIZED_VIEW for same name.
- **AUTO CDC flow sources MUST NOT contain system-reserved SCD2 columns
  (`__START_AT` / `__END_AT`)** — when a gold `dp.create_auto_cdc_flow` reads the CDF
  of a Silver SCD2 target (via `@dp.temporary_view`), drop/rename those two columns
  first or analysis fails with `DLTAnalysisException: Please rename the following
  system reserved columns in your source: __START_AT,__END_AT` (hit 2026-08-10 on
  `gold.dim_customer` + `gold.dim_asset`; other 12 gold flows were unaffected because
  their sources are SCD1).
- The user's hard requirement: silver AND gold layers must be **streaming tables** via
  the **latest LSDP API**; only `dim_date` (generated) and `fact_sensor_daily`
  (aggregate) remain MVs by documented design — be ready to defend that choice.