terraform {
  required_version = ">= 1.7.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
  }
}

resource "azurerm_databricks_workspace" "this" {
  name                        = "adb-${var.project_name}-${var.environment}-${var.location}"
  resource_group_name         = var.resource_group_name
  location                    = var.location
  sku                         = var.sku
  managed_resource_group_name = "databricks-rg-${var.project_name}-${var.environment}-${var.location}"

  custom_parameters {
    no_public_ip                                         = var.no_public_ip
    virtual_network_id                                   = var.virtual_network_id
    public_subnet_name                                   = var.public_subnet_name
    private_subnet_name                                  = var.private_subnet_name
    public_subnet_network_security_group_association_id  = var.public_subnet_nsg_id
    private_subnet_network_security_group_association_id = var.private_subnet_nsg_id
  }

  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Purpose     = "Databricks Lakehouse Compute Workspace"
    },
    var.additional_tags
  )
}
