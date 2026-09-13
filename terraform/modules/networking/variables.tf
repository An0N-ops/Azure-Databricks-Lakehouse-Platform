variable "project_name" {
  type        = string
  description = "Project name prefix."
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev, qa, prod)."
}

variable "location" {
  type        = string
  description = "Azure Region for VNet deployment."
}

variable "resource_group_name" {
  type        = string
  description = "Target Azure Resource Group name."
}

variable "vnet_cidr" {
  type        = string
  description = "CIDR block for the Virtual Network."
  default     = "10.100.0.0/16"
}

variable "public_subnet_cidr" {
  type        = string
  description = "CIDR block for Databricks host public subnet."
  default     = "10.100.1.0/24"
}

variable "private_subnet_cidr" {
  type        = string
  description = "CIDR block for Databricks host private subnet."
  default     = "10.100.2.0/24"
}

variable "service_endpoints" {
  type        = list(string)
  description = "Service endpoints enabled on the Databricks host subnets (e.g., Storage, KeyVault for firewall bypass)."
  default     = ["Microsoft.Storage", "Microsoft.KeyVault"]
}

variable "enable_nat_gateway" {
  type        = bool
  description = "Provision a NAT gateway for outbound internet egress from Databricks subnets. Required when the workspace uses no_public_ip."
  default     = true
}

variable "additional_tags" {
  type        = map(string)
  description = "Additional tags to append to networking resources."
  default     = {}
}
