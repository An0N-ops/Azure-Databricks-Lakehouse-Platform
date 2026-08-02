<div align="center">

# Azure Databricks Lakehouse Platform

A governed Azure Databricks Lakehouse reference platform: **Medallion storage, Unity Catalog governance, Lakeflow/Delta Live Tables pipelines, and modular Terraform IaC**.

[![Databricks](https://img.shields.io/badge/Databricks-DBR_14.3_LTS-blue.svg?logo=databricks&logoColor=white)](https://azure.microsoft.com/en-us/products/databricks)
[![Delta Lake](https://img.shields.io/badge/Delta_Lake-3.1-00ADEF.svg?logo=delta&logoColor=white)](https://delta.io/)
[![Terraform](https://img.shields.io/badge/Terraform-1.7.5-844FBA.svg?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![AzureRM](https://img.shields.io/badge/azurerm-5.0-0089D6.svg?logo=terraform&logoColor=white)](https://registry.terraform.io/providers/hashicorp/azurerm/latest)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/An0N-ops/Azure-Databricks-Lakehouse-Platform/actions/workflows/terraform-ci.yml/badge.svg)](.github/workflows/terraform-ci.yml)

</div>

## Platform Architecture

<img src="architecture/exports/platform-architecture.svg" alt="Platform architecture: source systems, ingestion, medallion lakehouse, governance, monitoring, consumers" width="100%" />

## What this is

A reference implementation of an enterprise data platform that moves an on-premises **Oracle ERP** estate (Fusion ERP, Database 19c, SFTP flat files, REST APIs) onto Azure. Data lands in an **ADLS Gen2 Delta Lakehouse** organized as Bronze → Silver → Gold, is governed end-to-end by **Unity Catalog**, and is transformed with **Delta Live Tables / Lakeflow Declarative Pipelines**.

It models a real consulting engagement rather than a feature-maximal template. Governance is provisioned before pipelines, and documented controls are limited to what is implemented — planned work lives in the roadmap, not in prose.

## Why this exists

- **A realistic modernization scenario** — heterogeneous legacy sources, batch windows of hours, siloed analytics, and no governance. Every abstraction exists because this scenario needs it.
- **Governance first** — Unity Catalog and identity are provisioned before any transformation exists.
- **Honest scope** — capabilities are claimed only when implemented; known limitations are documented as such.

## Quick Start

```bash
# 1. One-time: provision remote state storage (blob + locking)
cd terraform/bootstrap
terraform init && terraform apply -var="subscription_id=<SUBSCRIPTION_ID>" -var="location=eastus2"

# 2. Deploy the dev environment target
cd ../environments/dev
cp backend.tf.example backend.tf
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform plan -out=dev.tfplan && terraform apply dev.tfplan
```

Full deployment steps, prerequisites, and the OIDC CI/CD plan are in [`docs/deployment.md`](docs/deployment.md).

## Repository Structure

```text
.
├── terraform/             # Infrastructure as Code (Terraform)
│   ├── bootstrap/         # One-time remote state backend
│   ├── modules/           # resource_group · networking · storage · key_vault
│   │                      #   · databricks_workspace · unity_catalog
│   └── environments/      # Thin dev/qa/prod roots over a shared wrapper module
├── docs/                  # Deep-dive documentation (index: docs/README.md)
│   └── adr/               # Architecture Decision Records (ADR-001..007)
├── architecture/          # Platform diagram (SVG/PNG) and diagram sources
├── notebooks/             # Phase 3 — Medallion PySpark/SQL notebooks (bronze/silver/gold)
├── pipelines/             # Phase 3 — Delta Live Tables pipeline definitions
├── sample-data/           # Phase 3 — synthetic data schemas
├── scripts/               # Phase 3+ — automation and Databricks CLI utilities
├── tests/                 # Phase 3 — PySpark unit tests (pytest + chispa)
├── dashboards/            # Phase 4 — Databricks SQL / Power BI dashboard specs
├── .github/               # CI workflows, dependabot, PR/issue templates
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── CHANGELOG.md
└── LICENSE
```

## Documentation

| Area | Document |
| ---- | -------- |
| Architecture | [`docs/architecture.md`](docs/architecture.md) — components, Medallion zones, Unity Catalog model |
| Deployment | [`docs/deployment.md`](docs/deployment.md) — bootstrap, environments, OIDC plan |
| Development | [`docs/development.md`](docs/development.md) — local setup, Databricks Connect, PySpark/SQL standards |
| Security | [`docs/security.md`](docs/security.md) — governance model; [`SECURITY.md`](SECURITY.md) — policy + implemented/planned posture |
| Monitoring | [`docs/monitoring.md`](docs/monitoring.md) — system tables, DLT event logs, data quality |
| Cost | [`docs/cost-optimization.md`](docs/cost-optimization.md) — FinOps, cluster sizing, lifecycle |
| Roadmap | [`docs/project-roadmap.md`](docs/project-roadmap.md) — 5-phase plan |
| Decisions | [`docs/adr/README.md`](docs/adr/README.md) — ADR-001..007 |
| Terraform | [`terraform/environments/README.md`](terraform/environments/README.md) — environment targets & promotion |

## Roadmap

- **Phase 1 (done)** — repository foundation, governance, CI workflows.
- **Phase 2 (done)** — Terraform IaC: bootstrap, modules, Unity Catalog, `dev`/`qa`/`prod`, azurerm 5.0.
- **Phase 3 (next)** — Medallion pipelines: Bronze ingestion, Silver DLT, Gold star schema.
- **Phase 4** — monitoring, data quality, dashboards.
- **Phase 5** — OIDC automated deployment and production readiness.

## Design Philosophy

This is a governed-first lakehouse, not a generic data template. The full decision record is in [ADR-007](docs/adr/ADR-007-repository-design-philosophy.md).

- **Governance before pipelines** — Unity Catalog and identity are provisioned before any transformation exists.
- **Declarative and reviewable** — every environment is a code artifact; changes land via pull requests with checks.
- **Honest about scope** — documented controls are only those implemented; planned work lives in the roadmap, not in prose.
- **Medallion by default, with an escape hatch** — layered Bronze/Silver/Gold via DLT, plus plain PySpark/ADF where declarative tooling adds no value.
- **When NOT to use this architecture** — single-copy real-time serving, non-Azure deployments, or teams without the operational capacity for a governed lakehouse.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the branch model, conventional commits, and pre-commit checks. Report vulnerabilities per [`SECURITY.md`](SECURITY.md). All contributors follow the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

Distributed under the **Apache 2.0 License**. See [`LICENSE`](LICENSE).
