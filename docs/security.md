# Platform Security, Governance & Compliance Architecture

## Executive Security Model

The **Azure Databricks Lakehouse Platform** enforces strict enterprise security controls adhering to the **Zero Trust Architecture Model**, Microsoft Cloud Adoption Framework (CAF), and Databricks Security & Trust Center specifications.

---

## 1. Network Architecture & Isolation

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   Azure VNet (10.100.0.0/16)                           │
│                                                                        │
│  ┌──────────────────────────────┐    ┌──────────────────────────────┐  │
│  │ Host Public Subnet           │    │ Host Private Subnet          │  │
│  │ (10.100.1.0/24)              │    │ (10.100.2.0/24)              │  │
│  │ Databricks Control Plane Int │    │ Databricks Spark Workers     │  │
│  └──────────────┬───────────────┘    └──────────────┬───────────────┘  │
│                 │                                   │                  │
│                 └─────────────────┬─────────────────┘                  │
│                                   │                                    │
│                    Private Endpoints (Private Link)                    │
│                                   │                                    │
│       ┌───────────────────────────┼───────────────────────────┐        │
│       ▼                           ▼                           ▼        │
│ ┌───────────┐              ┌───────────────┐           ┌─────────────┐ │
│ │ ADLS Gen2 │              │ Unity Catalog │           │  Key Vault  │ │
│ └───────────┘              └───────────────┘           └─────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

- **VNet Injection**: Azure Databricks workspaces are deployed in dedicated Virtual Networks with custom Host Public and Host Private subnets. Public IPs on worker nodes are completely disabled (`no_public_ip = true`).
- **Private Endpoints (Azure Private Link)**: All traffic between Spark clusters, ADLS Gen2 storage accounts, Unity Catalog metastore, and Key Vault flows over private endpoints. Internet ingress/egress is restricted via Network Security Groups (NSGs).

---

## 2. Unity Catalog Fine-Grained Access Control (FGAC)

Access control operates exclusively through Unity Catalog's 3-level namespace (`catalog.schema.table`):

### A. Role-Based Access Control (RBAC) SQL Grants

```sql
-- Grant read access on Gold analytical schema to Data Analysts group
GRANT USAGE ON CATALOG prod_lakehouse TO `data_analysts`;
GRANT USAGE ON SCHEMA prod_lakehouse.gold TO `data_analysts`;
GRANT SELECT ON SCHEMA prod_lakehouse.gold TO `data_analysts`;

-- Restrict Bronze raw schema to Data Engineering Service Principal
GRANT ALL PRIVILEGES ON SCHEMA prod_lakehouse.bronze TO `sp_data_engineering`;
```

### B. Column-Level Dynamic Data Masking
PII fields (e.g., Social Security Numbers, Credit Card Numbers, Email addresses) are dynamically masked based on group membership:

```sql
CREATE OR REPLACE FUNCTION prod_lakehouse.shared.mask_email(email STRING)
RETURN CASE
  WHEN IS_ACCOUNT_GROUP_MEMBER('pii_admins') THEN email
  ELSE CONCAT(LEFT(email, 2), '***@***.', ELEMENT(SPLIT(email, '\\.'), -1))
END;

ALTER TABLE prod_lakehouse.silver.dim_customer
ALTER COLUMN email SET MASK prod_lakehouse.shared.mask_email;
```

### C. Row-Level Security Filters
Restrict dataset rows based on user organization or country assignment:

```sql
CREATE OR REPLACE FUNCTION prod_lakehouse.shared.region_filter(region_code STRING)
RETURN IS_ACCOUNT_GROUP_MEMBER('global_execs') OR region_code = CURRENT_USER();

ALTER TABLE prod_lakehouse.gold.fact_sales
SET ROW FILTER prod_lakehouse.shared.region_filter ON (region_code);
```

---

## 3. Secret Scopes & Encryption

- **Azure Key Vault Backed Secret Scopes**: Databricks notebook code and pipeline scripts never contain plain-text credentials. All secrets are stored in Azure Key Vault and referenced via DBUtils:

  ```python
  jdbc_password = dbutils.secrets.get(scope="akv-lakehouse-scope", key="oracle-jdbc-password")
  ```

- **Encryption Standards**:
  - **At Rest**: 256-bit AES encryption with Customer-Managed Keys (CMK) stored in Key Vault.
  - **In Transit**: TLS 1.2+ mandatory across all cluster nodes and storage endpoints.
