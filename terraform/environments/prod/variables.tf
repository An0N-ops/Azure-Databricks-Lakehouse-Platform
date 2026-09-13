variable "subscription_id" {
  type        = string
  description = "Azure Subscription ID used for environment resource provisioning."

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "subscription_id must be a valid GUID."
  }
}

variable "tenant_id" {
  type        = string
  description = "Azure AD / Entra ID Tenant ID for authentication and RBAC."

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.tenant_id))
    error_message = "tenant_id must be a valid GUID."
  }
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

  validation {
    condition     = can(regex("^[a-z0-9-]{2,20}$", var.project_name))
    error_message = "project_name must be 2-20 chars, lowercase alphanumeric plus hyphens."
  }
}

variable "environment" {
  type        = string
  description = "Deployment environment designation (dev, qa, prod)."

  validation {
    condition     = contains(["dev", "qa", "prod"], var.environment)
    error_message = "environment must be one of: dev, qa, prod."
  }
}

variable "location" {
  type        = string
  description = "Azure Region for environment resource placement."
  default     = "eastus2"
}

variable "vnet_cidr" {
  type        = string
  description = "CIDR block for the platform Virtual Network."
  default     = "10.102.0.0/16"

  validation {
    condition     = can(cidrhost(var.vnet_cidr, 0))
    error_message = "vnet_cidr must be a valid CIDR block."
  }
}

variable "public_subnet_cidr" {
  type        = string
  description = "CIDR block for the Databricks host public subnet."
  default     = "10.102.1.0/24"

  validation {
    condition     = can(cidrhost(var.public_subnet_cidr, 0))
    error_message = "public_subnet_cidr must be a valid CIDR block."
  }
}

variable "private_subnet_cidr" {
  type        = string
  description = "CIDR block for the Databricks host private subnet."
  default     = "10.102.2.0/24"

  validation {
    condition     = can(cidrhost(var.private_subnet_cidr, 0))
    error_message = "private_subnet_cidr must be a valid CIDR block."
  }
}

variable "enable_nat_gateway" {
  type        = bool
  description = "Provision a NAT gateway for Databricks subnet egress."
  default     = true
}

variable "storage_containers" {
  type        = list(string)
  description = "ADLS Gen2 filesystems provisioned in the environment."
  default     = ["bronze", "silver", "gold", "unity-catalog"]
}

variable "storage_account_replication_type" {
  type        = string
  description = "Storage replication strategy for the environment (LRS, ZRS, GRS)."
  default     = "GRS"

  validation {
    condition     = contains(["LRS", "ZRS", "GRS", "RAGRS"], var.storage_account_replication_type)
    error_message = "storage_account_replication_type must be one of: LRS, ZRS, GRS, RAGRS."
  }
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

variable "storage_network_default_action" {
  type        = string
  description = "Storage firewall default action."
  default     = "Allow"

  validation {
    condition     = contains(["Allow", "Deny"], var.storage_network_default_action)
    error_message = "storage_network_default_action must be Allow or Deny."
  }
}

variable "key_vault_network_default_action" {
  type        = string
  description = "Key Vault firewall default action."
  default     = "Allow"

  validation {
    condition     = contains(["Allow", "Deny"], var.key_vault_network_default_action)
    error_message = "key_vault_network_default_action must be Allow or Deny."
  }
}

variable "key_vault_purge_protection_enabled" {
  type        = bool
  description = "Enable Key Vault purge protection."
  default     = true
}

variable "unity_catalog_data_owner_group" {
  type        = string
  description = "Entra group granted USE/CREATE on the catalog. Empty disables grants."
  default     = ""
}

variable "unity_catalog_create_metastore" {
  type        = bool
  description = "Create a dedicated metastore in this environment. Set false with unity_catalog_metastore_id to use the shared metastore."
  default     = true
}

variable "unity_catalog_metastore_id" {
  type        = string
  description = "Shared metastore ID. Required when unity_catalog_create_metastore=false."
  default     = ""
}

variable "unity_catalog_data_access_is_default" {
  type        = bool
  description = "Mark this environment's data access as the metastore default."
  default     = true
}

variable "additional_tags" {
  type        = map(string)
  description = "Additional tags appended to all environment resources."
  default     = {}
}
