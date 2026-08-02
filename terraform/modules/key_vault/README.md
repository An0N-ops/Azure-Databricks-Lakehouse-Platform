# Azure Key Vault Module

## Purpose

Provisions a hardened **Azure Key Vault** that serves as the centralized secret store for the platform. Databricks notebooks, JDBC connections, and deployment automation reference credentials exclusively through an **Azure Key Vault backed secret scope** (`backend_type = "AZURE_KEYVAULT"`) — never through plain-text literals in code.

## Design Decisions

| Decision | Rationale |
| -------- | --------- |
| RBAC Authorization (`rbac_authorization_enabled`) | Replaces legacy access policies with Azure RBAC, aligning with the platform's zero-trust identity model. |
| Purge Protection + Soft Delete (90d) | Prevents permanent destruction of credentials; required by most enterprise compliance programs. |
| Random Name Suffix | Key Vault names are globally unique and capped at 24 characters; a 4-char suffix guarantees a valid, collision-free name. |

## Usage

```hcl
module "key_vault" {
  source              = "../../modules/key_vault"
  project_name        = "lakehouse"
  environment         = "dev"
  location            = "eastus2"
  resource_group_name = module.resource_group.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
}
```

## Integration

After deployment, a Databricks secret scope is registered against the vault URI:

```bash
databricks secrets create-scope \
  --scope akv-lakehouse-scope \
  --backend-type AZURE_KEYVAULT \
  --resource-id <key_vault_resource_id>
```

Notebooks then resolve credentials via `dbutils.secrets.get(scope = "akv-lakehouse-scope", key = "<secret>")`.

## Outputs

- `uri` — Vault URI consumed when creating the Databricks secret scope.
