output "name" {
  value       = azurerm_resource_group.this.name
  description = "Name of the provisioned Azure Resource Group."
}

output "id" {
  value       = azurerm_resource_group.this.id
  description = "Resource ID of the provisioned Azure Resource Group."
}

output "location" {
  value       = azurerm_resource_group.this.location
  description = "Azure Region location of the Resource Group."
}
