# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability or potential exposure within this repository or its Terraform/Databricks configurations:

> [!CAUTION]
> **Do NOT create a public GitHub Issue for security vulnerabilities.**

### Disclosure Process

1. **Private Notification**: Submit a report via [GitHub Security Advisories](https://github.com/An0N-ops/Azure-Databricks-Lakehouse-Platform/security/advisories) (preferred) or email `security@cloudarchitecture-consulting.com`.
2. **Report Contents**:
   - Component affected (e.g., Terraform HCL, Unity Catalog access control, Databricks Secret Scope, GitHub Actions workflow).
   - Step-by-step reproduction instructions or Proof of Concept (PoC).
   - Potential impact (e.g., privilege escalation, data leakage across Medallion layers, credential exposure).
3. **Response SLA**:
   - **Initial Acknowledgment**: Within 24 hours.
   - **Triage & Remediation Plan**: Within 72 hours.
   - **Patch Release**: Critical vulnerabilities patched within 7 business days.

---

## Implemented Security Controls

The controls below reflect what is currently implemented in this repository. Planned controls are listed separately in [Future Enhancements](#future-enhancements-phase-5-roadmap) and must not be treated as active posture.

### 1. Data Encryption & Storage

- **Encryption at Rest**: ADLS Gen2 Storage Accounts use Azure Storage Service Encryption (SSE) with Microsoft-managed keys.
- **Encryption in Transit**: Storage Account HTTPS-only traffic is enforced (AzureRM default `https_traffic_only = true`).
- **Hierarchical Namespace (HNS)**: Enabled on storage accounts for Azure AD-based directory and file ACLs.

### 2. Identity & Access Management (IAM)

- **Unity Catalog 3-Level Namespace**: Governance is modeled at `catalog.schema.table` level. The metastore, external locations, and per-environment `bronze`/`silver`/`gold` schemas are provisioned by Terraform; granular table and view grants are applied in Phase 3.
- **Managed Identities**: Unity Catalog storage access uses an Azure User-Assigned Managed Identity via a `databricks_metastore_data_access` storage credential. No service-principal secrets are embedded in Terraform.
- **Key Vault**: Azure Key Vault with RBAC authorization, soft-delete, and purge protection. Databricks Secret Scopes backed by Key Vault are configured in Phase 3.

### 3. Network Isolation

- **VNet Injection**: Databricks workspaces are deployed into a customer-managed VNet with dedicated host-public and host-private subnets delegated to `Microsoft.Databricks/workspaces`.
- **NSG Policy**: A Network Security Group is associated with both Databricks subnets. The required Databricks rule set is a known limitation tracked in [ADR-003](docs/adr/ADR-003-terraform.md) and will be completed before Phase 3 provisioning.

### 4. Secrets Management

- No credentials, connection strings, or tokens are committed to the repository. All variable example files use placeholder values.

---

## Automated Security Scanning

- **Gitleaks**: Scans commits and pull requests for hardcoded secrets, tokens, and certificates (`.github/workflows/secret-scanning.yml`).
- **Dependabot**: Automated dependency updates and vulnerability alerts for GitHub Actions and Terraform.

---

## Future Enhancements (Phase 5 Roadmap)

The following controls are planned but not yet implemented:

- **Customer-Managed Keys (CMK)** for ADLS Gen2 and Databricks managed disks.
- **Azure Private Link / Private Endpoints** for Databricks, ADLS Gen2, and Key Vault.
- **OIDC Federated Credentials** for GitHub Actions Azure authentication.
- **TFLint & Checkov** static analysis in CI.
- **Granular Unity Catalog grants** (table, column, row-level security) and Databricks Secret Scopes.
