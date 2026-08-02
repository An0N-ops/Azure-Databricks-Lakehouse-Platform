# Changelog

All notable changes to the **Azure Databricks Lakehouse Platform** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed
- **Security posture honesty**: `SECURITY.md` now documents only implemented controls; planned controls (Customer-Managed Keys, Private Link, OIDC, TFLint/Checkov) moved to a "Future Enhancements (Phase 5 Roadmap)" section.
- **Documentation consistency**: Runtime references aligned to DBR 14.3 LTS across `README.md`, `docs/development.md`, and `docs/cost-optimization.md`.
- **Architecture Decision Records**: Added `docs/adr/` with `ADR-001` through `ADR-007` covering Medallion, Unity Catalog, Terraform (including networking known limitations), Lakeflow Declarative Pipelines, DLT, GitHub Actions, and repository design philosophy.
- **CI/CD hardening**: All workflows scoped with least-privilege `permissions` and `concurrency` (stale-run cancellation); `paths` filters added; new `pr-conventions.yml` validates conventional commits and PR titles.
- **Pre-commit**: Added `.pre-commit-config.yaml` and `.commitlintrc.json`; `CONTRIBUTING.md` updated with installation and local verification steps.
- **Dependabot**: Terraform coverage expanded to `qa` and `prod`; removed `pip` ecosystem (no manifest yet).
- **Branching model**: `CONTRIBUTING.md` aligned to trunk-based topic branches (`main` + `feat|fix|docs|chore`); removed stale Git Flow references.
- **Python CI reliability**: Added `pyproject.toml` with Ruff configuration excluding Markdown documentation; formatted the Python samples in `docs/development.md` and `docs/security.md` so `ruff format --check` no longer fails on doc prose.
- **Terraform environment wrapper**: Consolidated the duplicated `dev`/`qa`/`prod` roots behind a shared `terraform/environments/modules/environment` module; each target is now a thin declaration with all wiring defined once.
- **Cross-platform line endings**: Added `.gitattributes` enforcing LF checkouts; markdownlint now ignores vendored `.terraform` and `node_modules` changelogs.
- **AzureRM provider 5.x upgrade**: Bumped `azurerm` constraint from `~> 3.90` to `~> 5.0` across all roots, the environment wrapper, and child modules; regenerated lock files to `5.0.1` and applied breaking-change fixes (`azurerm_storage_container` uses `storage_account_id`; `azurerm_key_vault` uses `rbac_authorization_enabled`).

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
