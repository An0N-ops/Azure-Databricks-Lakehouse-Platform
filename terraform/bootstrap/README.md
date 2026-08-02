# Terraform State Backend Bootstrap

## Purpose

This bootstrap module provisions a secure, highly-available Azure Storage Account and Blob Container to serve as the remote state backend for all platform environment targets (`dev`, `qa`, `prod`).

---

## Execution Guide

```bash
cd terraform/bootstrap

# Initialize local execution state
terraform init

# Review infrastructure plan
terraform plan -var="subscription_id=<YOUR_AZURE_SUBSCRIPTION_ID>" -out=bootstrap.tfplan

# Apply configuration
terraform apply bootstrap.tfplan
```

---

## Outputs

Upon completion, Terraform will output the generated Storage Account Name. Copy this value into your environment `backend.tf` files (`terraform/environments/dev/backend.tf`).
