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
  description = "Azure Region for Unity Catalog control-plane resources."
}

variable "resource_group_name" {
  type        = string
  description = "Target Azure Resource Group name."
}

variable "databricks_workspace_id" {
  type        = string
  description = "Numeric Databricks workspace ID to which the metastore is assigned."
}

variable "storage_account_name" {
  type        = string
  description = "ADLS Gen2 storage account name used to construct abfss:// external location URLs."
}

variable "medallion_containers" {
  type        = map(string)
  description = "Map of container name to Azure Resource ID for every medallion filesystem (bronze, silver, gold, unity-catalog)."
}

variable "metastore_container_name" {
  type        = string
  description = "Name of the container that hosts the Unity Catalog metastore root; excluded from external locations."
  default     = "unity-catalog"
}

variable "default_catalog_name" {
  type        = string
  description = "Name of the primary catalog created in the workspace (e.g., dev_lakehouse)."
}

variable "force_destroy" {
  type        = bool
  description = "Allow deletion of the metastore and its managed tables. Set to true only for non-production teardown."
  default     = false
}

variable "skip_validation" {
  type        = bool
  description = "Skip Databricks validation of the storage credential; required when role propagation lags access connector creation."
  default     = false
}

variable "additional_tags" {
  type        = map(string)
  description = "Additional tags to append to Azure Unity Catalog resources."
  default     = {}
}
