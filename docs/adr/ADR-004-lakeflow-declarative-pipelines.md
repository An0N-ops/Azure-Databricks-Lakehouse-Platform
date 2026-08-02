# ADR-004: Lakeflow Declarative Pipelines

- **Status**: Accepted
- **Date**: 2026-08-02
- **Deciders**: Platform Engineering

## Context

Pipeline definitions need to be source-controlled, reviewed, and re-deployed consistently across environments. Notebook-schedule orchestration hides the data flow in imperative code and fragments the pipeline lifecycle.

## Decision

Author pipelines declaratively using Databricks Lakeflow Declarative Pipelines where applicable, treating the pipeline definition (sources, expectations, targets) as data rather than procedural code. Complex, bespoke transformations remain available via shared PySpark modules.

## Consequences

- **Positive**: pipeline intent is reviewable in pull requests.
- **Positive**: consistent behavior across environments when re-deployed with environment variables.
- **Negative**: declarative abstractions can obscure complex logic; the shared-module escape hatch mitigates this.
- **Negative**: depends on Databricks platform support for the declarative authoring experience.

## Alternatives

- **Notebook-per-step with schedules**: rejected — logic hidden in notebooks, hard to version and review.
- **Azure Data Factory as transformation orchestrator**: retained only for source ingestion triggers; rejected for in-lake transforms in favor of DLT/Lakeflow.
