# Unity Catalog Module

## Purpose

Provision the complete **Unity Catalog** governance plane for a single environment: the account-level metastore, its managed-identity data access, the workspace assignment, and the medallion namespace (`catalog.schema`) that Phase 3 pipelines will target.

## Component Diagram

```text
┌────────────────────────── Account Level (Control Plane) ──────────────────────────┐
│                                                                                    │
│  databricks_metastore ── databricks_metastore_data_access (default)                │
│        │                                                                           │
│        └── databricks_storage_credential ── azure_managed_identity                 │
│                                                    │                               │
└────────────────────────────────────────────────────┼───────────────────────────────┘
                                                     │ access_connector_id
┌────────────────────────── Azure Resources ─────────▼───────────────────────────────┐
│  azurerm_user_assigned_identity ── azurerm_databricks_access_connector             │
│        └── Storage Blob Data Contributor (bronze/silver/gold/unity-catalog)        │
└────────────────────────────────────────────────────────────────────────────────────┘
                                                     │
┌────────────────────────── Workspace Level ─────────▼───────────────────────────────┐
│  databricks_metastore_assignment                                                   │
│  databricks_catalog  (dev_lakehouse)                                               │
│  ├── databricks_schema (bronze, silver, gold)                                      │
│  └── databricks_external_location (bronze/silver/gold abfss:// URLs)               │
└────────────────────────────────────────────────────────────────────────────────────┘
```

## Provisioning Order

1. **Identity**: User-Assigned Managed Identity + access connector, granted `Storage Blob Data Contributor` on every medallion container.
2. **Account Level**: metastore, storage credential (managed identity), and default data access configuration.
3. **Workspace Level**: metastore assignment, external locations, catalog, and medallion schemas.

> The access connector identity must hold blob permissions on the **Unity Catalog root container** before the metastore is created; if role propagation lags, set `skip_validation = true` on the storage credential.

## Usage

```hcl
module "unity_catalog" {
  source = "../../modules/unity_catalog"

  providers = {
    databricks.account   = databricks.account
    databricks.workspace = databricks.workspace
  }

  project_name            = "lakehouse"
  environment             = "dev"
  location                = "eastus2"
  resource_group_name     = module.resource_group.name
  databricks_workspace_id = module.databricks_workspace.workspace_id
  storage_account_name    = module.storage.name
  medallion_containers    = module.storage.containers
  default_catalog_name    = "dev_lakehouse"
}
```

## Outputs

- `metastore_id`, `metastore_name` — Account-level metastore identity.
- `catalog_name`, `schema_names` — Medallion namespace consumed by pipelines and CI.
- `external_locations` — Registered `abfss://` URLs for Bronze, Silver, and Gold.
