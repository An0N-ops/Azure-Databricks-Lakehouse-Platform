# ADR-007: Repository Design Philosophy

- **Status**: Accepted
- **Date**: 2026-08-02
- **Deciders**: Platform Engineering

## Context

Repositories fail when they optimize for completeness instead of clarity. This record fixes the engineering identity of this platform: what it optimizes for, what it deliberately does not do, and when it should not be used.

## Decision

### What this repository optimizes for

1. **Governance before pipelines.** Unity Catalog and identity are provisioned before any transformation exists. A lakehouse without governance is a data swamp; pipelines layered on governed storage stay correct as they scale.
2. **Declarative, reviewable infrastructure.** Every environment is a code artifact. Changes arrive as pull requests with checks, never as portal clicks.
3. **Honesty over feature count.** Security and capability claims reflect what is implemented. Planned work lives in the roadmap or in a "Future Enhancements" section, not in prose that implies it exists.
4. **Layered quality with an escape hatch.** Bronze/Silver/Gold is the default, enforced by DLT expectations — but plain PySpark or ADF remains available where declarative tooling adds no value.
5. **Fidelity to a real engagement.** The platform models a modernizing enterprise (Oracle ERP to lakehouse). Every abstraction exists because that scenario needs it, not for completeness.

### What this repository intentionally does not do

- Does not chase every Databricks feature; features earn their place by serving a stated decision.
- Does not hand-wave security or networking; known limitations are documented as such.
- Does not generate placeholder code; directories and modules exist only when they carry real content.

### When NOT to use this architecture

- **Single-copy, real-time serving** — the Medallion layers trade copy duplication for auditability and reprocessability.
- **Non-Azure deployments** — infrastructure and identity are Azure-bound by design.
- **Teams without operational capacity** for a governed lakehouse — Unity Catalog, DLT, and system tables require running discipline to justify their cost.
- **Prototypes and throwaway analytics** — the governance-first posture is overhead when the data has no lifecycle.

## Consequences

- **Positive**: consistent, defensible engineering decisions; a repository that reads like a design system rather than a template.
- **Negative**: intentionally narrow scope — some common features are omitted by design and must be justified to add.
- **Negative**: "honesty" posture surfaces limitations (e.g., NSG rules, Private Link) that a less rigorous repo would bury.

## Alternatives

- **Feature-maximal template**: rejected — breadth without decisions reads as noise to reviewers.
- **Minimal skeleton**: rejected — omits the governance layer that distinguishes a real platform.
