# Changelog

All notable changes to the **Azure Databricks Lakehouse Platform** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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
[0.2.0]: https://github.com/An0N-ops/Azure-Databricks-Lakehouse-Platform/releases/tag/v0.2.0
