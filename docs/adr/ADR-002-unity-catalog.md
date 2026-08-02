# ADR-002: Unity Catalog for Governance

- **Status**: Accepted
- **Date**: 2026-08-02
- **Deciders**: Platform Engineering

## Context

The platform needs centralized governance: fine-grained access control, auditability, and consistent data discovery across all compute. A Hive metastore plus per-workspace ACLs fragments security metadata and offers no unified audit trail.

## Decision

Use Unity Catalog as the single governance plane:

- One metastore per environment, attached to the environment workspace.
- Three-level namespace (`catalog.schema.table`) with a per-environment `{env}_lakehouse` catalog containing `bronze`, `silver`, and `gold` schemas.
- Storage access via a User-Assigned Managed Identity and a `databricks_metastore_data_access` storage credential — no embedded secrets.

## Consequences

- **Positive**: centralized, SQL-queryable security and audit via system tables, across all compute.
- **Positive**: managed-identity credential access eliminates service-principal secret management.
- **Negative**: one metastore per environment increases management surface.
- **Negative**: granular table/view grants are not yet applied (deferred to Phase 3).

## Alternatives

- **Hive Metastore**: rejected — no centralized cross-workspace governance or audit.
- **Multiple metastores per environment**: rejected — unnecessary complexity at this scale.
