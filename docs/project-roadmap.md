# Enterprise Project Roadmap

## Strategic Vision

The platform roadmap is a 5-phase engineering trajectory. Phases 1 and 2 are complete; implementation of the remaining phases is tracked here.

---

## Roadmap Phases

```mermaid
gantt
    title Platform Engineering Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 1: Foundation
    Repo Skeleton & Governance       :done, p1_1, 2026-08-01, 2026-08-03
    Architecture Documentation      :done, p1_2, 2026-08-02, 2026-08-04
    CI/CD Quality Workflows          :done, p1_3, 2026-08-03, 2026-08-05
    section Phase 2: Infrastructure
    Terraform Modules Provisioning   :done, p2_1, 2026-08-05, 2026-08-10
    Unity Catalog Metastore Setup    :done, p2_2, 2026-08-08, 2026-08-12
    Multi-Env Dev/QA/Prod Specs      :done, p2_3, 2026-08-10, 2026-08-15
    section Phase 3: Pipelines
    Bronze Ingestion Framework      :done, p3_1, 2026-08-15, 2026-08-22
    Silver Conformed Transformations : p3_2, 2026-08-20, 2026-08-28
    Gold Star Schema & DLT          : p3_3, 2026-08-25, 2026-09-02
    section Phase 4: Observability
    System Tables & Log Analytics   : p4_1, 2026-09-01, 2026-09-08
    Data Quality & Alerting         : p4_2, 2026-09-05, 2026-09-12
    section Phase 5: CI/CD & Production
    End-to-End Automated Deployment  : p5_1, 2026-09-10, 2026-09-20
```

---

## Detailed Milestone Deliverables

### Phase 1: Foundation & Governance (Completed)
- [x] Repository directory structure according to enterprise standards.
- [x] Documentation suite (`architecture.md`, `deployment.md`, `development.md`, etc.).
- [x] Governance policies (`SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `LICENSE`).
- [x] GitHub CI workflows for Markdown, Python (Ruff), YAML, Gitleaks Secret Scanning, and Terraform validation.

### Phase 2: Modular Infrastructure as Code (Terraform) (Completed)
- [x] One-time Azure remote state bootstrap module.
- [x] Reusable Terraform modules: `resource_group`, `networking`, `storage`, `key_vault`, `databricks_workspace`, `unity_catalog`.
- [x] Shared environment wrapper module with thin `dev`, `qa`, and `prod` roots.
- [x] Unity Catalog metastore, Access Connector (Managed Identity), storage credentials, external locations, catalogs, and medallion schemas.
- [x] AzureRM provider upgraded to `~> 5.0` with regenerated lock files.

### Phase 3: Medallion Data Pipelines & Delta Live Tables (Target Phase 3)
- [x] PySpark & Delta Live Tables (DLT) framework for Bronze Auto Loader ingestion (Oracle Fusion ERP, SFTP, REST APIs). Framework delivered: declarative Bronze manifest (`pipelines/energy/bronze_manifest.json`), shared Auto Loader helpers (`notebooks/shared/`), and a data-driven DLT notebook (`notebooks/bronze/ingest_energy.py`); wiring to real Oracle/SFTP/REST sources remains Phase 3.
- [ ] Silver layer conformed transformations, SCD Type 1/2 tracking, and schema validation.
- [ ] Gold layer star schema modeling (`fact_sales`, `dim_customer_360`, `kpi_financials`).

### Phase 4: Monitoring, Observability & Data Quality (Target Phase 4)
- [ ] Databricks System Tables queries for billing, cluster performance, and audit tracking.
- [ ] Integration with Azure Log Analytics workspace and Grafana / Databricks SQL dashboards.
- [ ] DLT event log parsing and Slack / Microsoft Teams incident alerting.

### Phase 5: End-to-End Release & Production Readiness (Target Phase 5)
- [ ] GitHub Actions OIDC automated Terraform deployment pipelines (`plan` on PR, `apply` on merge).
- [ ] Automated notebook integration test execution against Databricks staging workspace.
- [ ] Platform operational runbooks and performance benchmarks.

---

## Release Strategy

Every release corresponds to implemented functionality. Documentation-only releases stop at v0.2.0; milestones below are indicative and evolve as implementation progresses.

| Version | Milestone | Content |
| ------- | --------- | ------- |
| v0.2.0 | Foundation Complete | Architecture decisions, Terraform IaC, CI/CD, consolidated documentation. *(current)* |
| v0.3.0 | Terraform Infrastructure | First end-to-end apply; Databricks NSG rule set; workspace validation. |
| v0.4.0 | Bronze Layer Implementation | Auto Loader ingestion for Oracle ERP, SFTP, and REST sources. |
| v0.5.0 | Silver Layer & CDC | Conformed transformations, SCD Type 1/2, change data capture. |
| v0.6.0 | Gold Layer & Business Models | Star-schema models and business analytics tables. |
| v0.7.0 | Monitoring & Data Quality | System tables, DLT event logs, alerting, dashboards. |
| v0.8.0 | CI/CD & Deployment | OIDC automated plan/apply pipelines. |
| v0.9.0 | Performance Optimization | Cluster tuning, Photon, lifecycle and cost controls. |
| v1.0.0 | Enterprise Lakehouse Platform | Production-ready platform. |
