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
  description = "Azure Region for storage account placement."
}

variable "resource_group_name" {
  type        = string
  description = "Target Azure Resource Group name."
}

variable "containers" {
  type        = list(string)
  description = "List of ADLS Gen2 filesystems (containers) to provision within the lakehouse storage account."
  default     = ["bronze", "silver", "gold", "unity-catalog"]
}

variable "account_tier" {
  type        = string
  description = "Storage account performance tier."
  default     = "Standard"
}

variable "account_replication_type" {
  type        = string
  description = "Storage account replication strategy (LRS, GRS, ZRS, RA-GRS)."
  default     = "LRS"
}

variable "min_tls_version" {
  type        = string
  description = "Minimum supported TLS version for storage endpoints."
  default     = "TLS1_2"
}

variable "soft_delete_retention_days" {
  type        = number
  description = "Retention period (in days) for soft-deleted blobs and containers."
  default     = 30
}

variable "shared_access_key_enabled" {
  type        = bool
  description = "Allow storage account key access. Disable to enforce Entra ID only (Unity Catalog uses managed identity)."
  default     = false
}

variable "public_network_access_enabled" {
  type        = bool
  description = "Allow public network access. Set false only after private endpoints are configured."
  default     = true
}

variable "network_default_action" {
  type        = string
  description = "Storage firewall default action. Use Deny with allowed_subnet_ids for prod lockdown."
  default     = "Allow"

  validation {
    condition     = contains(["Allow", "Deny"], var.network_default_action)
    error_message = "network_default_action must be Allow or Deny."
  }
}

variable "allowed_subnet_ids" {
  type        = list(string)
  description = "Subnet resource IDs allowed through the storage firewall when network_default_action=Deny."
  default     = []
}

variable "cross_tenant_replication_enabled" {
  type        = bool
  description = "Allow cross-tenant replication. Disable for data exfiltration guardrail."
  default     = false
}

variable "additional_tags" {
  type        = map(string)
  description = "Additional tags to append to the storage account."
  default     = {}
}
