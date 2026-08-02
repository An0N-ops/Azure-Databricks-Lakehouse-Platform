output "resource_group_name" {
  value       = module.resource_group.name
  description = "Name of the environment Azure Resource Group."
}

output "resource_group_id" {
  value       = module.resource_group.id
  description = "Azure Resource ID of the environment Resource Group."
}

output "databricks_workspace_url" {
  value       = module.databricks_workspace.workspace_url
  description = "Databricks workspace console URL for the environment."
}

output "databricks_workspace_id" {
  value       = module.databricks_workspace.workspace_id
  description = "Numeric Databricks workspace ID for the environment."
}

output "databricks_workspace_resource_id" {
  value       = module.databricks_workspace.id
  description = "Azure Resource ID of the Databricks workspace (used for OIDC/CLI auth)."
}

output "storage_account_name" {
  value       = module.storage.name
  description = "ADLS Gen2 storage account name for the environment."
}

output "medallion_containers" {
  value       = module.storage.containers
  description = "Map of medallion container name to Azure Resource ID."
}

output "key_vault_uri" {
  value       = module.key_vault.uri
  description = "Azure Key Vault URI backing the Databricks secret scope."
}

output "unity_catalog_metastore_id" {
  value       = module.unity_catalog.metastore_id
  description = "Unity Catalog metastore ID for the environment."
}

output "unity_catalog_name" {
  value       = module.unity_catalog.catalog_name
  description = "Primary medallion catalog name for the environment."
}

output "unity_catalog_schemas" {
  value       = module.unity_catalog.schema_names
  description = "Medallion schema names (bronze, silver, gold) within the environment catalog."
}

output "unity_catalog_external_locations" {
  value       = module.unity_catalog.external_locations
  description = "Registered Unity Catalog external locations for the medallion zones."
}
