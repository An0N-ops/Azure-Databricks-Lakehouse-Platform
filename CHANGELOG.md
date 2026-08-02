# Changelog

All notable changes to the **Azure Databricks Lakehouse Platform** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
