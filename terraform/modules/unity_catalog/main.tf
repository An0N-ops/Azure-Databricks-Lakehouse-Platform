terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
    databricks = {
      source                = "databricks/databricks"
      version               = "~> 1.129"
      configuration_aliases = [databricks.account, databricks.workspace]
    }
  }
}

locals {
  credential_name = "${var.project_name}-${var.environment}-managed-identity"
}

resource "azurerm_user_assigned_identity" "this" {
  name                = "id-${var.project_name}-uc-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Purpose     = "Unity Catalog Metastore Access"
    },
    var.additional_tags
  )
}

resource "azurerm_databricks_access_connector" "this" {
  name                = "ac-${var.project_name}-uc-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.this.id]
  }

  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Purpose     = "Unity Catalog Metastore Access"
    },
    var.additional_tags
  )
}

resource "azurerm_role_assignment" "storage_blob_data_contributor" {
  for_each             = var.medallion_containers
  scope                = each.value
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
  # UAMI presents as a service principal; setting the type lets the provider
  # wait for AAD replication instead of failing with PrincipalNotFound.
  principal_type = "ServicePrincipal"
}

resource "databricks_metastore" "this" {
  provider      = databricks.account
  name          = "${var.project_name}-${var.environment}-metastore"
  region        = var.location
  force_destroy = var.force_destroy
}

resource "databricks_storage_credential" "this" {
  provider        = databricks.account
  name            = local.credential_name
  skip_validation = var.skip_validation

  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.this.id
  }

  # RBAC must propagate before Databricks validates the connector.
  depends_on = [azurerm_role_assignment.storage_blob_data_contributor]
}

resource "databricks_metastore_data_access" "this" {
  provider     = databricks.account
  metastore_id = databricks_metastore.this.id
  name         = "default"
  is_default   = true

  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.this.id
  }

  depends_on = [azurerm_role_assignment.storage_blob_data_contributor]
}

resource "databricks_metastore_assignment" "this" {
  provider             = databricks.workspace
  workspace_id         = var.databricks_workspace_id
  metastore_id         = databricks_metastore.this.id
  default_catalog_name = var.default_catalog_name
}

resource "databricks_external_location" "this" {
  for_each = {
    for name, id in var.medallion_containers : name => id
    if name != var.metastore_container_name
  }

  provider        = databricks.workspace
  name            = "${var.environment}-${each.key}"
  url             = "abfss://${each.key}@${var.storage_account_name}.dfs.core.windows.net/"
  credential_name = databricks_storage_credential.this.name

  depends_on = [databricks_metastore_assignment.this]
}

resource "databricks_catalog" "this" {
  provider = databricks.workspace
  name     = var.default_catalog_name
  comment  = "Primary ${var.environment} medallion catalog governed by Unity Catalog."

  properties = {
    environment = var.environment
    managed_by  = "terraform"
  }

  depends_on = [databricks_metastore_assignment.this]
}

resource "databricks_schema" "bronze" {
  provider     = databricks.workspace
  catalog_name = databricks_catalog.this.name
  name         = "bronze"
  comment      = "Raw append-only ingestion zone preserving source payloads and audit metadata."

  depends_on = [databricks_metastore_assignment.this]
}

resource "databricks_schema" "silver" {
  provider     = databricks.workspace
  catalog_name = databricks_catalog.this.name
  name         = "silver"
  comment      = "Conformed, cleansed, deduplicated entities with SCD Type 1/2 tracking."

  depends_on = [databricks_metastore_assignment.this]
}

resource "databricks_schema" "gold" {
  provider     = databricks.workspace
  catalog_name = databricks_catalog.this.name
  name         = "gold"
  comment      = "Analytics-ready Kimball star-schema models optimized for Databricks SQL and Power BI."

  depends_on = [databricks_metastore_assignment.this]
}

# Links the environment Key Vault to the workspace so notebooks/jobs can
# reference secrets via {{secrets/<scope>/<key>}} without storing them in code.
# Created only when the caller passes key_vault_id/uri (environment wrapper does).
resource "databricks_secret_scope" "key_vault" {
  count    = var.key_vault_id != "" && var.key_vault_uri != "" ? 1 : 0
  provider = databricks.workspace
  name     = "${var.environment}-keyvault"

  keyvault_metadata {
    resource_id = var.key_vault_id
    dns_name    = var.key_vault_uri
  }

  depends_on = [databricks_metastore_assignment.this]
}

# Least-privilege grants skeleton. Set data_owner_group (e.g., "data-engineers")
# to grant catalog/schema usage; empty (default) creates no grants so `validate`
# and fresh workspaces without groups still succeed.
resource "databricks_grants" "catalog" {
  count    = var.data_owner_group != "" ? 1 : 0
  provider = databricks.workspace
  catalog  = databricks_catalog.this.name

  grant {
    principal  = var.data_owner_group
    privileges = ["USE CATALOG", "USE SCHEMA", "CREATE SCHEMA", "CREATE TABLE", "CREATE VOLUME"]
  }

  depends_on = [databricks_metastore_assignment.this]
}

resource "databricks_grants" "schemas" {
  for_each = var.data_owner_group != "" ? {
    bronze = databricks_schema.bronze.name
    silver = databricks_schema.silver.name
    gold   = databricks_schema.gold.name
  } : {}

  provider = databricks.workspace
  schema   = "${databricks_catalog.this.name}.${each.value}"

  grant {
    principal  = var.data_owner_group
    privileges = ["USE SCHEMA", "CREATE TABLE", "CREATE VOLUME", "READ VOLUME"]
  }
}
