# Security Policy

## Enterprise Security & Governance Overview

The **Azure Databricks Lakehouse Platform** enforces defense-in-depth security principles aligning with the Microsoft Cloud Adoption Framework, Databricks Well-Architected Framework, and Unity Catalog Governance best practices.

---

## Supported Versions

We provide security updates and patches for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability or potential exposure within this repository or associated Terraform/Databricks configurations:

> [!CAUTION]
> **Do NOT create a public GitHub Issue for security vulnerabilities.**

### Disclosure Process

1. **Private Notification**: Submit a detailed vulnerability report via email to `security@cloudarchitecture-consulting.com` (or submit a private security advisory via GitHub Security Advisories).
2. **Report Contents**:
   - Component affected (e.g., Terraform HCL, Unity Catalog Access Control, Databricks Secret Scope, GitHub Actions workflow).
   - Step-by-step reproduction instructions or Proof of Concept (PoC).
   - Potential impact (e.g., privilege escalation, data leakage across Medallion layers, credential exposure).
3. **Response SLA**:
   - **Initial Acknowledgment**: Within 24 hours.
   - **Triage & Remediation Plan**: Within 72 hours.
   - **Patch Release**: Critical vulnerabilities patched within 7 business days.

---

## Security Baselines & Architecture

### 1. Data Security & Storage Encryption
- **Encryption at Rest**: ADLS Gen2 Storage Accounts use Azure Storage Service Encryption (SSE) with Customer-Managed Keys (CMK) stored in Azure Key Vault.
- **Encryption in Transit**: TLS 1.2+ mandatory across all network communication; HTTP explicitly disabled (`enable_https_traffic_only = true`).
- **Hierarchical Namespace (HNS)**: Enabled for fine-grained POSIX-compliant ACLs combined with Azure RBAC.

### 2. Identity & Access Management (IAM)
- **Unity Catalog 3-Level Namespace**: Access control is governed strictly at `catalog.schema.table` levels using explicit GRANT statement patterns.
- **Service Principals & Managed Identities**: Automated processes (ADF, GitHub Actions CI/CD) authenticate exclusively via Azure User-Assigned Managed Identities and OIDC federated credentials. Personal Access Tokens (PATs) are strictly prohibited in production.
- **Key Vault Secret Scopes**: Databricks Secret Scopes backed by Azure Key Vault are used to abstract all connection strings, JDBC credentials, and API tokens.

### 3. Network Isolation
- **VNet Injection**: Azure Databricks Workspaces are deployed into custom Virtual Networks with dedicated Host Public and Host Private subnets.
- **Private Endpoints**: Data traffic between Databricks, ADLS Gen2, and Azure Key Vault flows entirely over Private Link endpoints, bypassing public internet routing.

---

## Automated Security Scanning

This repository integrates automated security guardrails within CI/CD pipelines:

- **Gitleaks**: Scans commits and pull requests for hardcoded secrets, tokens, and certificates.
- **TFLint & Checkov**: Static code analysis for infrastructure misconfigurations in Terraform.
- **Dependabot**: Automated vulnerability scanning for Python PyPI packages and GitHub Actions.
