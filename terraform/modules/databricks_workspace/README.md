# Azure Databricks Workspace Module

## Purpose

Provisions an **Azure Databricks Premium workspace** deployed with custom VNet injection into the platform's dedicated network layer. Premium tier is mandatory for Unity Catalog support.

## Network Topology

```text
┌─────────────────────────── Azure VNet ───────────────────────────┐
│                                                                   │
│  ┌──────────────────────┐   ┌──────────────────────┐             │
│  │ Host Public Subnet   │   │ Host Private Subnet  │             │
│  │ Databricks Control   │   │ Spark Workers /      │             │
│  │ Plane / Webapp       │   │ Compute Nodes        │             │
│  └──────────────────────┘   └──────────────────────┘             │
└───────────────────────────┴───────────────────────────┴──────────┘
```

| Setting | Value | Rationale |
| ------- | ----- | --------- |
| `sku` | `premium` | Enables Unity Catalog, Delta Sharing, and System Tables. |
| `no_public_ip` | `true` | Nodes are private; all traffic flows through the injected VNet. |
| Managed Resource Group | `databricks-rg-*` | Azure creates compute/storage in a dedicated managed RG, isolated from the platform RG. |

## Usage

```hcl
module "databricks_workspace" {
  source                       = "../../modules/databricks_workspace"
  project_name                 = "lakehouse"
  environment                  = "dev"
  location                     = "eastus2"
  resource_group_name          = module.resource_group.name
  virtual_network_id           = module.networking.vnet_id
  public_subnet_name           = module.networking.public_subnet_name
  private_subnet_name          = module.networking.private_subnet_name
  public_subnet_nsg_id         = module.networking.network_security_group_id
  private_subnet_nsg_id        = module.networking.network_security_group_id
}
```

## Outputs

- `workspace_url` — Used as the `host` for the workspace-level Databricks provider.
- `workspace_id` — Used by `databricks_metastore_assignment`.
