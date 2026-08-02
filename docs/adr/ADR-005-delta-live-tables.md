# ADR-005: Delta Live Tables for Medallion Transformations

- **Status**: Accepted
- **Date**: 2026-08-02
- **Deciders**: Platform Engineering

## Context

Silver and Gold transformations require dependency management, incremental processing, and built-in data-quality controls. Ad-hoc PySpark scripts provide none of these out of the box.

## Decision

Use Delta Live Tables (DLT) for Bronze-to-Silver and Silver-to-Gold transformations:

- Declarative table definitions with `@dlt.table` and `@dlt.expect` quality contracts.
- Runtime-managed orchestration of table dependencies, retries, and incremental compute.
- DLT event log (`event_log`) as the source for observability and quality metrics.

## Consequences

- **Positive**: lineage, restartability, and incremental processing handled by the runtime.
- **Positive**: quality expectations enforced at layer boundaries (bronze-to-silver retain, silver drop-row, gold fail-update).
- **Negative**: DLT introduces runtime/vendor coupling.
- **Negative**: highly custom logic may be clearer as plain PySpark within a pipeline.

## Alternatives

- **Plain PySpark + job orchestration**: more control, but no built-in dependency graph, retries, or quality enforcement.
- **Stored procedures / plain SQL**: rejected — weak re-usability and observability.
