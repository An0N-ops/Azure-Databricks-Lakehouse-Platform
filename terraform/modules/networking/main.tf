terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }
}

resource "azurerm_virtual_network" "this" {
  name                = "vnet-${var.project_name}-${var.environment}-${var.location}"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.vnet_cidr]

  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.additional_tags
  )
}

# Split NSGs for least privilege. The legacy single NSG
# azurerm_network_security_group.databricks_nsg was renamed to .public;
# see moved block below. Private subnets get their own NSG.
resource "azurerm_network_security_group" "public" {
  name                = "nsg-${var.project_name}-databricks-public-${var.environment}-${var.location}"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.additional_tags
  )
}

resource "azurerm_network_security_group" "private" {
  name                = "nsg-${var.project_name}-databricks-private-${var.environment}-${var.location}"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.additional_tags
  )
}

moved {
  from = azurerm_network_security_group.databricks_nsg
  to   = azurerm_network_security_group.public
}

resource "azurerm_subnet" "public_subnet" {
  name                 = "sub-${var.project_name}-databricks-public-${var.environment}"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.public_subnet_cidr]

  dynamic "service_endpoint" {
    for_each = var.service_endpoints
    content {
      service = service_endpoint.value
    }
  }

  delegation {
    name = "databricks-delegation-public"

    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"
      ]
    }
  }
}

resource "azurerm_subnet" "private_subnet" {
  name                 = "sub-${var.project_name}-databricks-private-${var.environment}"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.private_subnet_cidr]

  dynamic "service_endpoint" {
    for_each = var.service_endpoints
    content {
      service = service_endpoint.value
    }
  }

  delegation {
    name = "databricks-delegation-private"

    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"
      ]
    }
  }
}

resource "azurerm_subnet_network_security_group_association" "public" {
  subnet_id                 = azurerm_subnet.public_subnet.id
  network_security_group_id = azurerm_network_security_group.public.id
}

resource "azurerm_subnet_network_security_group_association" "private" {
  subnet_id                 = azurerm_subnet.private_subnet.id
  network_security_group_id = azurerm_network_security_group.private.id
}

# Outbound egress for VNet-injected workspaces with no_public_ip=true.
# Without a NAT gateway, cluster nodes cannot reach PyPI, storage firewall
# allowlists, or the Databricks control plane relay reliably.
resource "azurerm_public_ip" "nat" {
  count               = var.enable_nat_gateway ? 1 : 0
  name                = "pip-${var.project_name}-nat-${var.environment}-${var.location}"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.additional_tags
  )
}

resource "azurerm_nat_gateway" "this" {
  count                   = var.enable_nat_gateway ? 1 : 0
  name                    = "nat-${var.project_name}-${var.environment}-${var.location}"
  location                = var.location
  resource_group_name     = var.resource_group_name
  sku_name                = "Standard"
  idle_timeout_in_minutes = 10

  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.additional_tags
  )
}

resource "azurerm_nat_gateway_public_ip_association" "this" {
  count                = var.enable_nat_gateway ? 1 : 0
  nat_gateway_id       = azurerm_nat_gateway.this[0].id
  public_ip_address_id = azurerm_public_ip.nat[0].id
}

resource "azurerm_subnet_nat_gateway_association" "public" {
  count          = var.enable_nat_gateway ? 1 : 0
  subnet_id      = azurerm_subnet.public_subnet.id
  nat_gateway_id = azurerm_nat_gateway.this[0].id
}

resource "azurerm_subnet_nat_gateway_association" "private" {
  count          = var.enable_nat_gateway ? 1 : 0
  subnet_id      = azurerm_subnet.private_subnet.id
  nat_gateway_id = azurerm_nat_gateway.this[0].id
}
