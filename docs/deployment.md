# Platform Deployment & Setup Guide

## Overview

This document provides step-by-step technical instructions for deploying the **Azure Databricks Lakehouse Platform** using Terraform Infrastructure as Code (IaC), Azure CLI, and GitHub Actions CI/CD workflows across **Development (`dev`)**, **QA (`qa`)**, and **Production (`prod`)** environments.

---

## Prerequisites

Before deploying the platform, ensure you have the following CLI tools and cloud credentials configured:

1. **Azure CLI**: Version 2.50.0+ (`az login` with Subscription Owner / Contributor permissions).
2. **Terraform**: Version 1.7.5+ (`terraform -v`).
3. **Databricks CLI**: Version 0.215.0+ (`databricks -v`).
4. **Python**: Version 3.11+ (`python --version`).
5. **Azure Subscription Permissions**:
   - `Owner` or `Contributor` + `User Access Administrator` on target subscription.
   - Global Administrator / Privileged Role Administrator (if creating Azure AD / Entra Service Principals).

---

## Step 1: Bootstrap Azure Remote State Backend

Terraform state must be stored securely in an Azure Storage Account with Blob leasing enabled to prevent concurrent state modifications.

```bash
# Navigate to Terraform bootstrap module
cd terraform/bootstrap

# Initialize Terraform
terraform init

# Review execution plan
terraform plan -out=bootstrap.tfplan \
  -var="subscription_id=00000000-0000-0000-0000-000000000000" \
  -var="location=eastus2" \
  -var="environment=shared"

# Provision remote state infrastructure
terraform apply bootstrap.tfplan
```

The bootstrap process creates:
- Resource Group: `rg-lakehouse-tfstate-shared-eastus2`
- ADLS Gen2 Storage Account: `stlakehousetfstate<random_suffix>`
- Blob Container: `tfstate`

---

## Step 2: Provision Infrastructure (Dev Environment)

Once the backend is bootstrapped, copy `backend.tf.example` to `backend.tf` and `terraform.tfvars.example` to `terraform.tfvars` in `terraform/environments/dev/`:

```bash
cd ../environments/dev

# Copy example configuration templates
cp backend.tf.example backend.tf
cp terraform.tfvars.example terraform.tfvars
```

Update `backend.tf` with the storage account name output from Step 1:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-lakehouse-tfstate-shared-eastus2"
    storage_account_name = "stlakehousetfstateshared"
    container_name       = "tfstate"
    key                  = "dev.terraform.tfstate"
  }
}
```

Apply the environment infrastructure:

```bash
# Initialize with remote backend
terraform init

# Validate configuration syntax
terraform validate

# Provision environment resources
terraform plan -out=dev.tfplan
terraform apply dev.tfplan
```

---

## Step 3: Configure GitHub Actions Azure OIDC Federated Credentials

For secure CI/CD deployment without stored credentials:

1. Create an Azure AD App Registration & Service Principal:

   ```bash
   az ad app create --display-name "github-actions-lakehouse-platform"
   ```

2. Configure Federated Identity Credentials for your GitHub Repository (`An0N-ops/Azure-Databricks-Lakehouse-Platform`):
   - **Subject Identifier**: `repo:An0N-ops/Azure-Databricks-Lakehouse-Platform:environment:dev`
3. Add GitHub Secrets to your repository:
   - `AZURE_CLIENT_ID`
   - `AZURE_TENANT_ID`
   - `AZURE_SUBSCRIPTION_ID`

---

## Step 4: Verify Workspace & Unity Catalog Setup

Verify that Databricks CLI can authenticate against the newly provisioned workspace:

```bash
# Set Databricks host URL
export DATABRICKS_HOST="https://adb-XXXXXXXXXXXXXXXX.XX.azuredatabricks.net"

# Verify CLI connection
databricks clusters list

# Verify Unity Catalog metastore association
databricks metastores list
```

---

## Step 5: Deploy the Lakeflow Pipelines with Databricks Asset Bundles

The Bronze/Silver/Gold Lakeflow pipelines are packaged as a Databricks
Asset Bundle in `bundle/databricks.yml` and released by the
`Databricks Bundle CI/CD` GitHub Actions workflow. The bundle declares the three
pipelines and three targets; catalog and landing-path values are bundle
variables per target:

| Target | Mode | Branch | Catalog | Landing root |
| ------ | ---- | ------ | ------- | ------------ |
| `dev` | development | feature branches | `dev_lakehouse` | `abfss://bronze@stlakehousedevelop.../landing` |
| `qa` | production | `develop` | `qa_lakehouse` | `abfss://bronze@stlakehouseqa.../landing` |
| `prod` | production | `main` | `prod_lakehouse` | `abfss://bronze@stlakehouseprod.../landing` |

> Update the `workspace.host` placeholders and the storage-account suffix in
> each target's `landing_path` with the values output by Terraform
> (`databricks_workspace` URL and `storage_account_name`).

### CI/CD Behavior

- **Pull requests** that touch `bundle/**`, `notebooks/**`, or `pipelines/**`
  run offline structural validation (`scripts/validate_bundle.py`) — no
  workspace required.
- **Workspace validation** (`databricks bundle validate --target <env>
  --strict`) and **deploys** are gated on workspace credentials
  (`DATABRICKS_HOST`, `DATABRICKS_TOKEN`) being configured; until Phase 5 wires
  up OIDC, only the offline checks run.
- **Branch-driven deploys**: merge to `main` deploys `prod`, merge to `develop`
  deploys `qa`, and pushes to feature branches deploy `dev`.

### Required GitHub Secrets

| Secret | Purpose |
| ------ | ------- |
| `DATABRICKS_HOST` | Workspace URL, e.g. `https://adb-...azuredatabricks.net`. |
| `DATABRICKS_TOKEN` | Databricks PAT with `CAN_MANAGE` on the pipelines. |
| `DATABRICKS_SERVICE_PRINCIPAL` | Application ID for `run_as` on production-mode targets. |

### Deploying from a Local Machine

```bash
# From the repository root; the CLI looks for bundle/databricks.yml
export DATABRICKS_HOST="https://adb-...azuredatabricks.net"
export DATABRICKS_TOKEN="dapi..."

cd bundle
databricks bundle validate --target dev
databricks bundle deploy --target dev --auto-approve
```

See [`docs/briefs/deployment-bundles.md`](briefs/deployment-bundles.md) for the
feature brief and design rationale.
