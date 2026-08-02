output "id" {
  value       = azurerm_databricks_workspace.this.id
  description = "Azure Resource ID of the provisioned Databricks workspace."
}

output "workspace_id" {
  value       = azurerm_databricks_workspace.this.workspace_id
  description = "Numeric Databricks workspace ID used for metastore assignment."
}

output "workspace_url" {
  value       = azurerm_databricks_workspace.this.workspace_url
  description = "Workspace console URL used to configure the Databricks workspace-level provider."
}

output "managed_resource_group_name" {
  value       = azurerm_databricks_workspace.this.managed_resource_group_name
  description = "Name of the Azure managed resource group created by Databricks for cluster infrastructure."
}
