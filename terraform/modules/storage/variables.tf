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

variable "additional_tags" {
  type        = map(string)
  description = "Additional tags to append to the storage account."
  default     = {}
}
