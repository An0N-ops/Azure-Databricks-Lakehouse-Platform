# Terraform Environment Targets

Each directory under `terraform/environments/` represents an isolated platform lifecycle target. All targets consume the same reusable modules from `terraform/modules/`; only parameter values differ.

| Target | Catalog | Replication | Guardrails |
| ------ | ------- | ----------- | ---------- |
| `dev` | `dev_lakehouse` | LRS | Fast iteration, relaxed validation |
| `qa`  | `qa_lakehouse`  | ZRS | Production-parity data, staged promotion |
| `prod`| `prod_lakehouse`| GRS | Strictest controls, no teardown |

## Environment Contract

Every target exposes an identical output contract:

- `databricks_workspace_url` / `databricks_workspace_resource_id` — consumed by the Databricks CLI and Phase 5 OIDC deployment.
- `unity_catalog_name` / `unity_catalog_schemas` — namespace targeted by Delta Live Tables pipelines.
- `unity_catalog_external_locations` — `abfss://` URLs for the medallion zones.
- `medallion_containers` — ADLS Gen2 filesystem resource IDs.

## Promotion Workflow

```text
feature branch ──> terraform plan (dev) ──> merge to main
        │                                        │
        └── apply (dev)                          ├── apply (qa)
                                                 └── apply (prod)  [release/*]
```

## Deploying a Target

```bash
cd terraform/environments/dev

# Materialize local configuration from committed templates
cp backend.tf.example backend.tf
cp terraform.tfvars.example terraform.tfvars

# Update backend.tf with the storage account from the bootstrap phase, then:
terraform init
terraform plan -out=dev.tfplan
terraform apply dev.tfplan
```

> `backend.tf` and `terraform.tfvars` are git-ignored; only the `.example` templates are committed so CI can run `terraform init -backend=false && terraform validate` without credentials.
