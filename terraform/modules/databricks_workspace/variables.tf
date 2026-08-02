variable "project_name" {
  type        = string
  description = "Project name prefix used for standardized resource naming."
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev, qa, prod)."
}

variable "location" {
  type        = string
  description = "Azure Region for Databricks workspace placement."
}

variable "resource_group_name" {
  type        = string
  description = "Target Azure Resource Group name."
}

variable "sku" {
  type        = string
  description = "Databricks workspace pricing tier (premium required for Unity Catalog)."
  default     = "premium"
}

variable "virtual_network_id" {
  type        = string
  description = "Azure Resource ID of the Virtual Network hosting the workspace subnets."
}

variable "public_subnet_name" {
  type        = string
  description = "Name of the Databricks host public subnet within the target VNet."
}

variable "private_subnet_name" {
  type        = string
  description = "Name of the Databricks host private subnet within the target VNet."
}

variable "public_subnet_nsg_id" {
  type        = string
  description = "Azure Resource ID of the Network Security Group bound to the public subnet."
}

variable "private_subnet_nsg_id" {
  type        = string
  description = "Azure Resource ID of the Network Security Group bound to the private subnet."
}

variable "no_public_ip" {
  type        = bool
  description = "Disable public IP addresses on Databricks cluster nodes (VNet-injected, private networking)."
  default     = true
}

variable "additional_tags" {
  type        = map(string)
  description = "Additional tags to append to the Databricks workspace."
  default     = {}
}
