variable "databricks_account_id" {
  type        = string
  description = "Databricks Account Console ID used by the account-level provider."
}

variable "databricks_auth_type" {
  type        = string
  description = "Authentication strategy for the Databricks provider (azure-cli, azure-client-secret, etc.)."
  default     = "azure-cli"
}

variable "project_name" {
  type        = string
  description = "Project name prefix used for the shared metastore name."
  default     = "lakehouse"

  validation {
    condition     = can(regex("^[a-z0-9-]{2,20}$", var.project_name))
    error_message = "project_name must be 2-20 chars, lowercase alphanumeric plus hyphens."
  }
}

variable "location" {
  type        = string
  description = "Azure region for the shared metastore. Must match the environment regions."
  default     = "eastus2"
}
