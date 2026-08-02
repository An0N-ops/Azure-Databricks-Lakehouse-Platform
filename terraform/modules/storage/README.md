# ADLS Gen2 Storage Module

## Purpose

Provisions the platform's core **Azure Data Lake Storage Gen2 (ADLS Gen2)** account and the medallion-architecture filesystems that back the Bronze, Silver, and Gold layers, plus the dedicated container used as the Unity Catalog metastore root.

## Design Decisions

| Decision | Rationale |
| -------- | --------- |
| Hierarchical Namespace (`is_hns_enabled`) | Required for ADLS Gen2 semantics, path-based ACLs, and Databricks Auto Loader directory listings. |
| Medallion Containers | `bronze`, `silver`, `gold`, `unity-catalog` map one-to-one with Unity Catalog external locations and the metastore root. |
| Versioning + Soft Delete (30d) | Protection against accidental deletes and corrupt writes; consistent with enterprise data protection SLAs. |
| Public Access Disabled | `allow_blob_public_access` and `allow_nested_items_to_be_public` are locked to `false`. |
| Random Name Suffix | Storage account names are globally unique; a deterministic 6-char suffix avoids collisions across environments. |

## Access Model

Databricks and the Unity Catalog metastore access this storage through **identity-based authentication** (User-Assigned Managed Identity) rather than storage account keys. Role assignments (`Storage Blob Data Contributor`) are applied by the `unity_catalog` module for the exact containers the platform requires.

## Usage

```hcl
module "storage" {
  source                     = "../../modules/storage"
  project_name               = "lakehouse"
  environment                = "dev"
  location                   = "eastus2"
  resource_group_name        = module.resource_group.name
  account_replication_type   = "LRS"
}
```

## Outputs

- `name` — Storage account name (used to construct `abfss://` external location URLs).
- `containers` — Map of container name to Azure Resource ID, consumed by `unity_catalog` for role assignments.
