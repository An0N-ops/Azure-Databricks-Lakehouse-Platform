# Security & Governance

The implemented security posture is defined in [`SECURITY.md`](../SECURITY.md) (policy, supported versions, reporting, and an explicit implemented-vs-planned split). This document describes the Unity Catalog governance model the platform is built on.

## Governance Model

Access control operates exclusively through Unity Catalog's 3-level namespace (`catalog.schema.table`). The metastore, external locations, and per-environment `bronze`/`silver`/`gold` schemas are provisioned by Terraform; granular grants are applied in Phase 3.

### Role-based grants

```sql
GRANT USAGE ON CATALOG prod_lakehouse TO `data_analysts`;
GRANT USAGE ON SCHEMA prod_lakehouse.gold TO `data_analysts`;
GRANT SELECT ON SCHEMA prod_lakehouse.gold TO `data_analysts`;

GRANT ALL PRIVILEGES ON SCHEMA prod_lakehouse.bronze TO `sp_data_engineering`;
```

### Column-level dynamic masking

PII fields are masked based on group membership:

```sql
CREATE OR REPLACE FUNCTION prod_lakehouse.shared.mask_email(email STRING)
RETURN CASE
  WHEN IS_ACCOUNT_GROUP_MEMBER('pii_admins') THEN email
  ELSE CONCAT(LEFT(email, 2), '***@***.', ELEMENT(SPLIT(email, '\\.'), -1))
END;

ALTER TABLE prod_lakehouse.silver.dim_customer
ALTER COLUMN email SET MASK prod_lakehouse.shared.mask_email;
```

### Row-level filters

```sql
CREATE OR REPLACE FUNCTION prod_lakehouse.shared.region_filter(region_code STRING)
RETURN IS_ACCOUNT_GROUP_MEMBER('global_execs') OR region_code = CURRENT_USER();

ALTER TABLE prod_lakehouse.gold.fact_sales
SET ROW FILTER prod_lakehouse.shared.region_filter ON (region_code);
```

## Secrets Management

Databricks code and pipelines never contain plain-text credentials. Secrets are stored in Azure Key Vault (RBAC authorization, soft-delete, purge protection) and referenced through a Key Vault-backed Databricks secret scope:

```python
jdbc_password = dbutils.secrets.get(
    scope="akv-lakehouse-scope", key="oracle-jdbc-password"
)
```

## Network & Encryption Posture

- **Implemented**: VNet-injected Databricks workspaces with dedicated host-public and host-private subnets (`no_public_ip = true`), Storage Service Encryption (SSE) at rest with Microsoft-managed keys, HTTPS-only traffic.
- **Planned (Phase 5)**: Azure Private Link / private endpoints, Customer-Managed Keys, and the full Databricks NSG rule set. Known limitations are tracked in [ADR-003](adr/ADR-003-terraform.md).

See [`SECURITY.md`](../SECURITY.md) for the authoritative implemented/planned list.
