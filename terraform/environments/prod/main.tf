terraform {
  required_version = ">= 1.7.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.43"
    }
  }
}

# Thin root: all resource wiring and provider configuration live in the
# shared `modules/environment` wrapper so the three targets stay identical
# and environment-specific values are expressed only via terraform.tfvars.
module "environment" {
  source = "../modules/environment"

  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id

  databricks_account_id = var.databricks_account_id
  databricks_auth_type  = var.databricks_auth_type

  project_name = var.project_name
  environment  = var.environment
  location     = var.location

  vnet_cidr           = var.vnet_cidr
  public_subnet_cidr  = var.public_subnet_cidr
  private_subnet_cidr = var.private_subnet_cidr

  storage_containers               = var.storage_containers
  storage_account_replication_type = var.storage_account_replication_type

  metastore_container_name      = var.metastore_container_name
  unity_catalog_force_destroy   = var.unity_catalog_force_destroy
  unity_catalog_skip_validation = var.unity_catalog_skip_validation

  additional_tags = var.additional_tags
}
