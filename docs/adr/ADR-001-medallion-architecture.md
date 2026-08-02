# ADR-001: Medallion Architecture

- **Status**: Accepted
- **Date**: 2026-08-02
- **Deciders**: Platform Engineering

## Context

Source data arrives in heterogeneous forms (Oracle exports, SFTP flat files, REST APIs) with no consistent schema, quality, or lineage guarantees. Consumers have conflicting needs: raw, reproducible copies for audit; conformed entities for analytics; and curated models for BI. Storing and serving a single copy cannot satisfy all three.

## Decision

Adopt the Medallion architecture with three explicit layers, each backed by a Unity Catalog schema under a per-environment catalog:

- **Bronze** (`raw`): raw ingestion via Auto Loader, preserving source payloads plus ingestion metadata.
- **Silver** (`cleansed`): conformed, validated entities with schema enforcement, SCD Type 1/2 tracking, and DLT expectations.
- **Gold** (`analytics`): Kimball star-schema models tuned for Databricks SQL Serverless and Power BI.

Layers are independently reprocessable, and quality gates are enforced at each boundary.

## Consequences

- **Positive**: clear lineage, layered quality enforcement, and independent reprocessing of any layer.
- **Positive**: maps cleanly onto DLT, Delta Lake, and Unity Catalog primitives.
- **Negative**: three physical copies of the data; storage cost must be managed with lifecycle policies.
- **Negative**: extra transformation hops add latency — unsuitable for single-copy, real-time serving.

## Alternatives

- **Single conformed layer**: simpler, but couples raw and curated concerns and blocks auditability and reprocessing. Rejected.
- **Feature-store/ML-first layout**: premature; analytics is the primary consumer today. Rejected.
