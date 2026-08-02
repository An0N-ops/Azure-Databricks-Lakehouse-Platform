output "resource_group_name" {
  value       = azurerm_resource_group.tfstate.name
  description = "Name of the Azure Resource Group housing the Terraform state storage account."
}

output "storage_account_name" {
  value       = azurerm_storage_account.tfstate.name
  description = "Name of the Azure Storage Account configured for remote Terraform state."
}

output "container_name" {
  value       = azurerm_storage_container.tfstate.name
  description = "Name of the Blob Container storing environment state files."
}

output "backend_config_template" {
  value       = <<EOF
terraform {
  backend "azurerm" {
    resource_group_name  = "${azurerm_resource_group.tfstate.name}"
    storage_account_name = "${azurerm_storage_account.tfstate.name}"
    container_name       = "${azurerm_storage_container.tfstate.name}"
    key                  = "<environment>.terraform.tfstate"
  }
}
EOF
  description = "Backend configuration block template for environment configurations."
}
