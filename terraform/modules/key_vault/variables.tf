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

variable "enable_rbac_authorization" {
  type        = bool
  description = "Use Azure RBAC for data-plane authorization instead of legacy access policies."
  default     = true
}

variable "additional_tags" {
  type        = map(string)
  description = "Additional tags to append to the Key Vault."
  default     = {}
}
