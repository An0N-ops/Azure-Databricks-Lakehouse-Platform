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

output "public_network_security_group_id" {
  value       = azurerm_network_security_group.public.id
  description = "Azure Resource ID of the Databricks public-subnet Network Security Group."
}

output "private_network_security_group_id" {
  value       = azurerm_network_security_group.private.id
  description = "Azure Resource ID of the Databricks private-subnet Network Security Group."
}

output "network_security_group_id" {
  value       = azurerm_network_security_group.public.id
  description = "Deprecated: use public_network_security_group_id. Kept for backward compatibility."
}

output "nat_gateway_id" {
  value       = var.enable_nat_gateway ? azurerm_nat_gateway.this[0].id : null
  description = "Azure Resource ID of the egress NAT gateway (null when enable_nat_gateway=false)."
}

output "nat_public_ip" {
  value       = var.enable_nat_gateway ? azurerm_public_ip.nat[0].ip_address : null
  description = "Public IP of the egress NAT gateway (null when enable_nat_gateway=false)."
}
