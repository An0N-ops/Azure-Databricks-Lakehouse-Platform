output "metastore_id" {
  value       = databricks_metastore.this.id
  description = "Azure Databricks Unity Catalog metastore ID."
}

output "metastore_name" {
  value       = databricks_metastore.this.name
  description = "Name of the provisioned Unity Catalog metastore."
}

output "catalog_name" {
  value       = databricks_catalog.this.name
  description = "Name of the primary medallion catalog."
}

output "schema_names" {
  value       = [databricks_schema.bronze.name, databricks_schema.silver.name, databricks_schema.gold.name]
  description = "Names of the medallion schemas (bronze, silver, gold) created within the catalog."
}

output "external_locations" {
  value       = { for k, v in databricks_external_location.this : k => { name = v.name, url = v.url } }
  description = "Map of medallion zone to its registered Unity Catalog external location."
}

output "access_connector_id" {
  value       = azurerm_databricks_access_connector.this.id
  description = "Azure Resource ID of the Unity Catalog access connector (User-Assigned Managed Identity)."
}

output "managed_identity_principal_id" {
  value       = azurerm_user_assigned_identity.this.principal_id
  description = "Object (principal) ID of the User-Assigned Managed Identity backing Unity Catalog data access."
}
