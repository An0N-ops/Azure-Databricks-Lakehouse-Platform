# Changelog

All notable changes to the **Azure Databricks Lakehouse Platform** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **LSDP terminology sweep of the documentation suite**
  (`27e60a9`): `docs/{architecture,deployment,development,monitoring,
  project-roadmap}.md`, `docs/briefs/*` and `docs/demo/runbook.md` restyled
  from the legacy `dlt` API to Lakeflow Spark Declarative Pipelines (`dp`)
  naming; ADRs and the migration session notes intentionally remain as
  historical records.
- **Observability foundation (Milestone A, first slice)**:
  `scripts/observability_report.py` — a pure-Python, CLI-driven report that
  runs the eight-section Databricks-native query set (job runs via
  `system.lakeflow.*`, table freshness via UC `information_schema`, row
  volumes, warehouse query health and slowest queries via
  `system.query.history`, cost by day/SKU via `system.billing.usage`, audit
  via `system.access.audit`) against a live workspace through the SQL
  Statements API. Every query in the set is validated against the dev
  workspace; `docs/monitoring.md` rewritten from design-only into measured
  reality (real output samples, pipeline-event-log CLI steps for updates and
  quality events).

---

## [0.3.0] - 2026-08-10

_End-to-End Lakehouse Reference Implementation._ This release marks the point
where the repository is working software rather than a design: deterministic
enterprise data generation, a governed medallion lakehouse with SCD Type 1
**and** SCD Type 2, quality expectations at every boundary, deployment through
Databricks Asset Bundles against a live workspace, and an AI/BI dashboard on
the resulting Gold data.

### Added
- **Synthetic Enterprise Data Generator** (`sample-data/`): config-driven,
  deterministic generator with a domain-agnostic core and an Energy/Oil & Gas
  reference pack (`NorthGrid Resources`, 14 related entities; customers,
  locations, assets, employees, inventory, work orders, maintenance events,
  weather, IoT telemetry). Output is CSV/JSON/Parquet with date-partitioned
  batches and a provenance `manifest.json`; covered by pytest and a CI smoke
  run.
- **Bronze Ingestion Framework** (Phase 3): declarative Auto Loader ingestion
  driven by `pipelines/energy/bronze_manifest.json` (one spec per entity:
  landing source, CSV options, quality expectations) rendering append-only
  streaming tables with audit columns, Change Data Feed, and the ADR-005
  retain policy (violations flagged in the event log, never dropped).
- **Silver Conformed Layer** (Phase 3): declarative conformed transformations
  driven by `pipelines/energy/silver_manifest.json` (one spec per entity:
  Bronze source, SCD keys, per-column conforming rules, quality expectations)
  with SCD upserts — **SCD Type 1 by default**, and **SCD Type 2** on
  `customers` (`account_status`, `credit_rating`) and `assets`
  (`asset_status`, `criticality`) via `"scd_type": 2` + `track_by`, with
  `ignore_null_keys` honored. SCD2 semantics are pinned by a pure-Python
  oracle (`notebooks/shared/scd2.py` + `tests/test_scd2.py`): initial
  version, close/open on tracked change, exactly one current version per key,
  no history on repeated identical records, in-place absorption of untracked
  changes, null-key rows ignored.
- **Gold Star-Schema Layer** (Phase 3): declarative Kimball models driven by
  `pipelines/energy/gold_manifest.json` — dimensions conform Silver entities,
  `dim_date` is generated from a declared `date_range`, facts derive a
  `YYYYMMDD` `date_key` and optionally aggregate measures at a declared grain.
  Gold expectations use the ADR-005 fail policy (abort rather than publish a
  broken analytics table).
- **Lakeflow Spark Declarative Pipelines (LSDP) migration**: all layers moved
  from the legacy `dlt` API to `pyspark.pipelines as dp`
  (`dp.table` / `dp.temporary_view` / `dp.materialized_view` /
  `dp.create_auto_cdc_flow`, `dp.expect*`); `silver_source_*` are pipeline
  temporary views streamed from the Bronze Change Data Feed; Gold AUTO CDC
  flows drop the reserved SCD2 `__START_AT`/`__END_AT` columns before
  analysis. Handoff notes in `docs/pipeline-fix-session-notes.md`.
- **Data quality expectations** on every layer with explicit policies:
  retain at the Bronze→Silver boundary, fail at the Silver→Gold boundary.
- **Databricks Asset Bundles (DABs) deployment** (`bundle/`): the
  Bronze/Silver/Gold Lakeflow pipelines and the AI/BI dashboard are packaged
  in a single declarative bundle (`bundle/databricks.yml`) with `dev`/`qa`/
  `prod` targets and per-target catalog/landing variables; validated by a
  pure-Python structural validator (`scripts/validate_bundle.py`) in CI and
  deployed against a live workspace. Brief at
  `docs/briefs/deployment-bundles.md`.
- **Deployed AI/BI dashboard**: *NorthGrid Energy Operations* querying the
  Gold star schema.
- **Feature Briefs** (`docs/briefs/`): every platform feature framed as a
  consulting brief (Business Problem, Solution, Expected Outcome,
  Dependencies, Implementation) with a new index.
- **Demo & evidence layer** (`docs/demo/`): evidence checklist with real
  screenshot placeholders and a reproducible runbook covering data generation
  → bundle validate/deploy → pipeline run → Bronze/Silver/Gold verification
  (including SCD2 checks) → quality events → dashboard.

### Known Limitations

- Real enterprise source systems are represented through synthetic/reference
  data (the Energy pack is fictional by design).
- OIDC automated Terraform/Databricks deployment is future work; today's
  workspace deployment is driven by the local `databricks bundle` flow.
- Private Link and fully private networking remain future work.
- Advanced production observability (System Tables, Log Analytics, incident
  alerting) remains future work (roadmap Milestone A).
- The AI/BI dashboard is deployed in the dev environment only.

---

## [0.2.0] - 2026-08-02

_Foundation Complete._ The engineering foundation is finished: architecture decisions are recorded, infrastructure is fully expressed in Terraform, CI/CD is hardened, and the documentation suite is consolidated and frozen. From this release onward, versions track implemented functionality rather than documentation.

### Added
- **Architecture Decision Records**: `docs/adr/` with `ADR-001` through `ADR-007` (plus template and index) covering Medallion, Unity Catalog, Terraform (including networking known limitations), Lakeflow Declarative Pipelines, DLT, GitHub Actions, and repository design philosophy.
- **Terraform environment wrapper**: consolidated `dev`/`qa`/`prod` wiring into a shared `terraform/environments/modules/environment` module; each target is now a thin declaration.
- **Pre-commit & commit conventions**: `.pre-commit-config.yaml`, `.commitlintrc.json`, and a PR title/commit validation workflow.
- **Architecture diagram**: color-scheme-aware `architecture/exports/platform-architecture.svg` (with PNG fallback); `docs/README.md` navigation index; consolidated `architecture/README.md`.
- **Python CI reliability**: `pyproject.toml` Ruff configuration excluding Markdown documentation.

### Changed
- **Security posture honesty**: `SECURITY.md` documents only implemented controls; planned controls (Customer-Managed Keys, Private Link, OIDC, TFLint/Checkov) moved to "Future Enhancements".
- **CI/CD hardening**: least-privilege `permissions`, `concurrency` groups with stale-run cancellation, and explicit `paths` filters across all workflows.
- **AzureRM provider 5.x**: constraint bumped to `~> 5.0` across all roots, the environment wrapper, and child modules; lock files regenerated to `5.0.1`; breaking-change fixes applied (`azurerm_storage_container` uses `storage_account_id`; `azurerm_key_vault` uses `rbac_authorization_enabled`).
- **Documentation freeze (Phase 2)**: `README.md` rewritten as a landing page (hero, architecture diagram, quick start, documentation links); duplicated Mermaid diagram, technology-stack, and key-features sections removed; marketing prose trimmed across `docs/*`; `docs/security.md` aligned with the `SECURITY.md` posture; `ADR-003` and roadmap statuses corrected.
- **Dependabot**: Terraform coverage expanded to `qa` and `prod`; removed `pip` ecosystem (no manifest yet).
- **Branching model**: `CONTRIBUTING.md` aligned to trunk-based topic branches; cross-platform LF line endings via `.gitattributes`.

### Known Limitations
- The Databricks NSG rule set for VNet-injected subnets is not yet defined (tracked in [ADR-003](docs/adr/ADR-003-terraform.md)); validated at first apply.
- `no_public_ip = true` without Private Link; a fully private workspace requires the Phase 5 Private Link work.
- CI validates Terraform configuration but does not plan/apply; automated deployment is Phase 5 (OIDC-based).
- Cost guidance (Spot VMs, Photon, lifecycle policies) is documented but not yet implemented.

### What's Next
- **v0.3.0 — Terraform Infrastructure**: first end-to-end apply against a real subscription, the Databricks NSG rule set, and validation of workspace provisioning. See [`docs/project-roadmap.md`](docs/project-roadmap.md) for the release strategy.

---

## [0.1.0] - 2026-08-02

### Added
- **Repository Architecture Skeleton**: Initial enterprise project structure for Medallion Lakehouse platform.
- **Enterprise Documentation Suite**:
  - `docs/architecture.md`: Comprehensive enterprise modernization architectural design.
  - `docs/deployment.md`: Environment setup and Azure OIDC CI/CD deployment guide.
  - `docs/development.md`: Developer guide (Databricks Connect v2, PySpark, testing standards).
  - `docs/project-roadmap.md`: 5-Phase strategic engineering roadmap.
  - `docs/monitoring.md`: Observability, System Tables, DLT event logging strategy.
  - `docs/security.md`: Enterprise security baseline, Private Link, and Unity Catalog governance.
  - `docs/cost-optimization.md`: FinOps framework for Databricks compute and ADLS storage.
- **Governance & Standards**: `LICENSE` (Apache 2.0), `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/dependabot.yml`, GitHub Issue Templates (`bug_report.yml`, `feature_request.yml`).
- **GitHub CI Workflows**:
  - Markdown syntax linting (`markdown-lint.yml`).
  - Python linting & formatting with Ruff (`python-ci.yml`).
  - YAML syntax validation (`yaml-lint.yml`).
  - Secret scanning with Gitleaks (`secret-scanning.yml`).
  - Terraform validation & linting (`terraform-ci.yml`).
- **Phase 2 Terraform Infrastructure**:
  - `terraform/bootstrap/`: Backend state storage account, container, and state lock roles.
  - `terraform/modules/`: Modular enterprise HCL specs for Resource Groups, VNet Networking (Host Public/Private subnets), ADLS Gen2 Storage, Key Vault, Databricks Premium Workspace, and Unity Catalog Metastore & Medallion Schemas.
  - `terraform/environments/`: Production-grade environment definitions for `dev`, `qa`, and `prod`.

---

[Unreleased]: https://github.com/An0N-ops/Azure-Databricks-Lakehouse-Platform/compare/v0.2.0...HEAD
[0.3.0]: https://github.com/An0N-ops/Azure-Databricks-Lakehouse-Platform/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/An0N-ops/Azure-Databricks-Lakehouse-Platform/releases/tag/v0.2.0
