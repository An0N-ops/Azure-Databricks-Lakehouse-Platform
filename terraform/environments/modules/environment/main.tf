terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.129"
    }
  }
}

data "azurerm_client_config" "current" {}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
  # azurerm v5 defaults to no RP auto-registration; register only what the lakehouse needs.
  # Microsoft.Compute is required for the Databricks managed RG (VMs/disks).
  resource_providers_to_register = [
    "Microsoft.Authorization",
    "Microsoft.Compute",
    "Microsoft.Databricks",
    "Microsoft.KeyVault",
    "Microsoft.ManagedIdentity",
    "Microsoft.Network",
    "Microsoft.Resources",
    "Microsoft.Storage",
  ]
}

provider "databricks" {
  alias      = "account"
  host       = "https://accounts.azuredatabricks.net"
  account_id = var.databricks_account_id
  auth_type  = var.databricks_auth_type
}

provider "databricks" {
  alias                       = "workspace"
  host                        = module.databricks_workspace.workspace_url
  azure_workspace_resource_id = module.databricks_workspace.id
  auth_type                   = var.databricks_auth_type
}

module "resource_group" {
  source          = "../../../modules/resource_group"
  project_name    = var.project_name
  environment     = var.environment
  location        = var.location
  additional_tags = var.additional_tags
}

module "networking" {
  source              = "../../../modules/networking"
  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = module.resource_group.name
  vnet_cidr           = var.vnet_cidr
  public_subnet_cidr  = var.public_subnet_cidr
  private_subnet_cidr = var.private_subnet_cidr
  enable_nat_gateway  = var.enable_nat_gateway
  additional_tags     = var.additional_tags
}

module "storage" {
  source                   = "../../../modules/storage"
  project_name             = var.project_name
  environment              = var.environment
  location                 = var.location
  resource_group_name      = module.resource_group.name
  containers               = var.storage_containers
  account_replication_type = var.storage_account_replication_type
  network_default_action   = var.storage_network_default_action
  allowed_subnet_ids = [
    module.networking.public_subnet_id,
    module.networking.private_subnet_id,
  ]
  additional_tags = var.additional_tags
}

module "key_vault" {
  source                   = "../../../modules/key_vault"
  project_name             = var.project_name
  environment              = var.environment
  location                 = var.location
  resource_group_name      = module.resource_group.name
  tenant_id                = data.azurerm_client_config.current.tenant_id
  purge_protection_enabled = var.key_vault_purge_protection_enabled
  network_default_action   = var.key_vault_network_default_action
  allowed_subnet_ids = [
    module.networking.public_subnet_id,
    module.networking.private_subnet_id,
  ]
  additional_tags = var.additional_tags
}

module "databricks_workspace" {
  source                = "../../../modules/databricks_workspace"
  project_name          = var.project_name
  environment           = var.environment
  location              = var.location
  resource_group_name   = module.resource_group.name
  virtual_network_id    = module.networking.vnet_id
  public_subnet_name    = module.networking.public_subnet_name
  private_subnet_name   = module.networking.private_subnet_name
  public_subnet_nsg_id  = module.networking.public_network_security_group_id
  private_subnet_nsg_id = module.networking.private_network_security_group_id
  additional_tags       = var.additional_tags
}

module "unity_catalog" {
  source = "../../../modules/unity_catalog"

  providers = {
    databricks.account   = databricks.account
    databricks.workspace = databricks.workspace
  }

  project_name             = var.project_name
  environment              = var.environment
  location                 = var.location
  resource_group_name      = module.resource_group.name
  databricks_workspace_id  = module.databricks_workspace.workspace_id
  storage_account_name     = module.storage.name
  medallion_containers     = module.storage.containers
  metastore_container_name = var.metastore_container_name
  default_catalog_name     = "${var.environment}_lakehouse"
  force_destroy            = var.unity_catalog_force_destroy
  skip_validation          = var.unity_catalog_skip_validation
  key_vault_id             = module.key_vault.id
  key_vault_uri            = module.key_vault.uri
  data_owner_group         = var.unity_catalog_data_owner_group
  additional_tags          = var.additional_tags

  depends_on = [module.databricks_workspace]
}
