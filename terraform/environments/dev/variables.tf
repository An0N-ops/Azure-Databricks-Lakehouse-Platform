variable "subscription_id" {
  type        = string
  description = "Azure Subscription ID used for environment resource provisioning."
}

variable "tenant_id" {
  type        = string
  description = "Azure AD / Entra ID Tenant ID for authentication and RBAC."
}

variable "databricks_account_id" {
  type        = string
  description = "Databricks Account Console ID used by the account-level Unity Catalog provider."
}

variable "databricks_auth_type" {
  type        = string
  description = "Authentication strategy for the Databricks providers (azure-cli, azure-client-secret, etc.)."
  default     = "azure-cli"
}

variable "project_name" {
  type        = string
  description = "Project name prefix used for standardized resource naming."
  default     = "lakehouse"
}

variable "environment" {
  type        = string
  description = "Deployment environment designation (dev, qa, prod)."
}

variable "location" {
  type        = string
  description = "Azure Region for environment resource placement."
  default     = "eastus2"
}

variable "vnet_cidr" {
  type        = string
  description = "CIDR block for the platform Virtual Network."
  default     = "10.100.0.0/16"
}

variable "public_subnet_cidr" {
  type        = string
  description = "CIDR block for the Databricks host public subnet."
  default     = "10.100.1.0/24"
}

variable "private_subnet_cidr" {
  type        = string
  description = "CIDR block for the Databricks host private subnet."
  default     = "10.100.2.0/24"
}

variable "storage_containers" {
  type        = list(string)
  description = "ADLS Gen2 filesystems provisioned in the environment."
  default     = ["bronze", "silver", "gold", "unity-catalog"]
}

variable "storage_account_replication_type" {
  type        = string
  description = "Storage replication strategy for the environment (LRS, ZRS, GRS)."
  default     = "LRS"
}

variable "metastore_container_name" {
  type        = string
  description = "Container hosting the Unity Catalog metastore root; excluded from external locations."
  default     = "unity-catalog"
}

variable "unity_catalog_force_destroy" {
  type        = bool
  description = "Allow deletion of metastore-managed tables. Enable only for non-production teardown."
  default     = false
}

variable "unity_catalog_skip_validation" {
  type        = bool
  description = "Skip storage credential validation to tolerate RBAC propagation lag."
  default     = false
}

variable "additional_tags" {
  type        = map(string)
  description = "Additional tags appended to all environment resources."
  default     = {}
}
