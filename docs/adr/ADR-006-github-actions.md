# ADR-006: GitHub Actions for CI/CD

- **Status**: Accepted
- **Date**: 2026-08-02
- **Deciders**: Platform Engineering

## Context

The repository needs automated quality gates (linting, validation, secret scanning) with minimal operational overhead and native GitHub integration. CI/CD is a first-class review requirement for every pull request.

## Decision

Use GitHub Actions as the CI/CD platform:

- Workflows for Markdown, YAML, Python (Ruff), secret scanning (Gitleaks), and Terraform validation.
- Conventional-commit and PR-title validation to keep repository history clean.
- Least-privilege `permissions: contents: read` and `concurrency` groups that cancel stale runs.

## Consequences

- **Positive**: zero external CI infrastructure; checks co-located with the repository.
- **Positive**: consistent with the contribution model in `CONTRIBUTING.md`.
- **Negative**: Azure plan/apply is deferred to Phase 5 (OIDC-based) — CI validates, it does not deploy.
- **Negative**: misconfigured `paths` filters could skip checks; filters are kept explicit per workflow.

## Alternatives

- **Azure DevOps Pipelines**: strong Azure integration, but splits CI and contribution tooling across two systems.
- **Jenkins / self-hosted runners**: rejected — operational overhead without benefit at this scale.
