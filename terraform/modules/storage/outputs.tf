output "id" {
  value       = azurerm_storage_account.this.id
  description = "Azure Resource ID of the provisioned ADLS Gen2 storage account."
}

output "name" {
  value       = azurerm_storage_account.this.name
  description = "Name of the provisioned ADLS Gen2 storage account."
}

output "primary_blob_endpoint" {
  value       = azurerm_storage_account.this.primary_blob_endpoint
  description = "Primary blob service endpoint of the storage account."
}

output "containers" {
  value       = { for c in var.containers : c => azurerm_storage_data_lake_gen2_filesystem.this[c].id }
  description = "Map of container name to Azure Resource ID for each provisioned ADLS Gen2 filesystem."
}
