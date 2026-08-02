# ADR-003: Terraform for Infrastructure as Code

- **Status**: Accepted
- **Date**: 2026-08-02
- **Deciders**: Platform Engineering

## Context

Azure infrastructure must be reproducible, reviewable, and auditable across `dev`, `qa`, and `prod`. Manual portal provisioning does not scale and leaves no review trail.

## Decision

Manage all cloud infrastructure with Terraform (AzureRM + Databricks providers):

- A `bootstrap` module provisions remote state storage with locking.
- Reusable modules under `terraform/modules/`: `resource_group`, `networking`, `storage`, `key_vault`, `databricks_workspace`, `unity_catalog`.
- Thin environment roots under `terraform/environments/{dev,qa,prod}` with distinct redundancy tiers (LRS/ZRS/GRS).
- Providers pinned, multi-platform lock files committed, `backend.tf` and `*.tfvars` gitignored.

## Consequences

- **Positive**: declarative review trail and drift detection via `terraform plan`.
- **Positive**: environment parity through shared modules.
- **Negative**: CI validates configuration but does not plan/apply (Phase 5, OIDC-based).
- **Negative**: environment roots were refactored behind a shared wrapper module (`terraform/environments/modules/environment`); thin roots remain declaratively duplicated per target by design.

## Known Limitations

### Databricks NSG rules

The NSG associated with the Databricks subnets is created without an explicit rule set (`terraform/modules/networking/main.tf`). Azure Databricks VNet injection requires a specific rule set (control-plane 443, worker node 22/443/3306/6666). Until defined, workspace provisioning and cluster management may fail functional checks. Plan: implement the required rules before Phase 3 provisioning, validated against the Databricks secure-cluster-connectivity documentation.

### no_public_ip

`no_public_ip = true` is set on the Databricks workspace (`terraform/modules/databricks_workspace/main.tf`). On Azure this is most meaningful in combination with Private Link. Current decision: keep the flag and validate at first apply; document Private Link (Phase 5) as the prerequisite for a fully private workspace.

## Alternatives

- **Bicep/ARM**: Azure-native, but no Databricks-first module ecosystem comparable to the Databricks Terraform provider.
- **Pulumi**: viable, but Terraform is the de-facto standard for multi-cloud and Databricks infrastructure.
