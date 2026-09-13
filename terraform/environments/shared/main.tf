terraform {
  required_version = ">= 1.9.0"
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.129"
    }
  }
}

# Shared regional metastore. Deploy once per region BEFORE the dev/qa/prod
# environments, then point each environment at it via:
#   unity_catalog_create_metastore       = false
#   unity_catalog_metastore_id           = "<shared metastore_id output>"
#   unity_catalog_data_access_is_default = false  # keep true in exactly one env
provider "databricks" {
  alias      = "account"
  host       = "https://accounts.azuredatabricks.net"
  account_id = var.databricks_account_id
  auth_type  = var.databricks_auth_type
}

resource "databricks_metastore" "shared" {
  provider      = databricks.account
  name          = "${var.project_name}-shared-metastore"
  region        = var.location
  force_destroy = false
}
