# Architecture Decision Records

This directory records the significant architecture decisions for the Azure Databricks Lakehouse Platform. ADRs are lightweight records of *why* the platform is engineered the way it is — not documentation of what the code does.

## Index

| ADR | Decision |
| --- | -------- |
| [ADR-001](ADR-001-medallion-architecture.md) | Medallion architecture |
| [ADR-002](ADR-002-unity-catalog.md) | Unity Catalog for governance |
| [ADR-003](ADR-003-terraform.md) | Terraform for infrastructure as code |
| [ADR-004](ADR-004-lakeflow-declarative-pipelines.md) | Lakeflow Declarative Pipelines |
| [ADR-005](ADR-005-delta-live-tables.md) | Delta Live Tables for transformations |
| [ADR-006](ADR-006-github-actions.md) | GitHub Actions for CI/CD |
| [ADR-007](ADR-007-repository-design-philosophy.md) | Repository design philosophy |

## Status Convention

- **Accepted**: decision is in effect and expected to persist.
- **Superseded**: decision has been replaced by a newer ADR (referenced in the record).
- **Proposed**: under discussion, not yet in effect.
- **Deprecated**: decision no longer applies; superseding record may be empty for short-lived items.

## Adding a New ADR

1. Copy `ADR-000-template.md` to `ADR-NNN-short-title.md`.
2. Fill in every section; keep it concise and technical.
3. Add the record to the index table above.
4. Open a PR. Every ADR change is reviewed like any other code change.

ADRs are immutable once merged. To change a decision, add a new ADR that supersedes the old one rather than editing history.
