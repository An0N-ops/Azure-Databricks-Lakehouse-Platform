output "vnet_id" {
  value       = azurerm_virtual_network.this.id
  description = "Azure Resource ID of the provisioned Virtual Network."
}

output "vnet_name" {
  value       = azurerm_virtual_network.this.name
  description = "Name of the provisioned Virtual Network."
}

output "public_subnet_id" {
  value       = azurerm_subnet.public_subnet.id
  description = "Azure Resource ID of the Databricks host public subnet."
}

output "public_subnet_name" {
  value       = azurerm_subnet.public_subnet.name
  description = "Name of the Databricks host public subnet."
}

output "private_subnet_id" {
  value       = azurerm_subnet.private_subnet.id
  description = "Azure Resource ID of the Databricks host private subnet."
}

output "private_subnet_name" {
  value       = azurerm_subnet.private_subnet.name
  description = "Name of the Databricks host private subnet."
}

output "network_security_group_id" {
  value       = azurerm_network_security_group.databricks_nsg.id
  description = "Azure Resource ID of the shared Databricks Network Security Group."
}
