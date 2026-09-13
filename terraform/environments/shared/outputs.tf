output "metastore_id" {
  value       = databricks_metastore.shared.id
  description = "Shared Unity Catalog metastore ID. Pass as unity_catalog_metastore_id in dev/qa/prod with unity_catalog_create_metastore=false."
}

output "metastore_name" {
  value       = databricks_metastore.shared.name
  description = "Name of the shared Unity Catalog metastore."
}
