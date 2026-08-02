output "id" {
  value       = azurerm_key_vault.this.id
  description = "Azure Resource ID of the provisioned Key Vault."
}

output "name" {
  value       = azurerm_key_vault.this.name
  description = "Name of the provisioned Key Vault."
}

output "uri" {
  value       = azurerm_key_vault.this.vault_uri
  description = "Vault URI used when creating the Databricks Azure Key Vault backed secret scope."
}
