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
  description = "Azure Region for Key Vault placement."
}

variable "resource_group_name" {
  type        = string
  description = "Target Azure Resource Group name."
}

variable "tenant_id" {
  type        = string
  description = "Azure AD / Entra ID Tenant ID that owns the Key Vault."
}

variable "sku_name" {
  type        = string
  description = "Key Vault SKU (standard or premium)."
  default     = "standard"
}

variable "soft_delete_retention_days" {
  type        = number
  description = "Retention period (in days) for soft-deleted secrets, keys, and certificates."
  default     = 90
}

variable "purge_protection_enabled" {
  type        = bool
  description = "Enable purge protection to prevent permanent deletion of secrets."
  default     = true
}

variable "rbac_authorization_enabled" {
  type        = bool
  description = "Use Azure RBAC for data-plane authorization instead of legacy access policies."
  default     = true
}

variable "public_network_access_enabled" {
  type        = bool
  description = "Allow public network access. Set false only after private endpoints are configured."
  default     = true
}

variable "network_default_action" {
  type        = string
  description = "Key Vault firewall default action. Use Deny with allowed networks for prod lockdown."
  default     = "Allow"

  validation {
    condition     = contains(["Allow", "Deny"], var.network_default_action)
    error_message = "network_default_action must be Allow or Deny."
  }
}

variable "allowed_subnet_ids" {
  type        = list(string)
  description = "Subnet resource IDs allowed through the Key Vault firewall when network_default_action=Deny."
  default     = []
}

variable "allowed_ip_rules" {
  type        = list(string)
  description = "IP/CIDR rules allowed through the Key Vault firewall when network_default_action=Deny."
  default     = []
}

variable "additional_tags" {
  type        = map(string)
  description = "Additional tags to append to the Key Vault."
  default     = {}
}
