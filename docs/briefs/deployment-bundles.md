# Feature Brief: Databricks Asset Bundles Deployment

Every feature in this platform is documented as a consulting brief — the
business problem it solves, the solution, the expected outcome, and how it is
implemented. This is the **deployment brief**: how the Bronze/Silver/Gold Lakeflow
pipelines are packaged, validated, and released to dev, qa, and prod.

## Business Problem

The medallion Lakeflow pipelines are code, but today they have no release pipeline.
Notebooks and manifests are reviewed as source, yet nobody has answered *how the
pipelines actually get to a workspace*. Deploying a Lakeflow pipeline by
hand means:

- **Manual, error-prone releases** — clicking through the Databricks UI to
  recreate a pipeline, with no single source of truth for its settings.
- **Environment drift** — the catalog, landing path, and cluster settings are
  retyped per environment and silently diverge.
- **No change detection** — a pull request that touches a notebook or manifest
  gives no signal about which pipeline it affects or whether the deployment is
  still valid.
- **No provenance** — there is no record of *what* was deployed *where* or
  *when*, which blocks audit and rollback.

## Solution

**Databricks Asset Bundles (DABs)** — the platform's native IaC for Databricks
resources — package all three Lakeflow pipelines and their environments in a single
declarative definition, `bundle/databricks.yml`, plus a GitHub Actions workflow
(`.github/workflows/dab-ci-cd.yml`) that validates every change and deploys by
branch.

- **One bundle, three environments**: the three pipelines
  (`energy_bronze`, `energy_silver`, `energy_gold`) reference the existing Lakeflow
  notebooks and declare their Unity Catalog schema, cluster, and pipeline cluster
  environment variables. Catalog and landing path come from bundle variables, so
  the same definition promotes across `dev`, `qa`, and `prod` unchanged — the
  exact `{placeholder}` strategy the manifests already use.
- **Manifest placeholders flow through**: `DATABRICKS_CATALOG` and
  `DATABRICKS_LANDING_PATH` are set as `spark_env_vars` on each pipeline cluster from
  the bundle variables, so the notebooks resolve `{catalog}` and `{landing}`
  exactly as they do in a local Databricks Connect run.
- **Validation without a workspace**: `databricks bundle validate` needs live
  workspace credentials (available only in Phase 5). Until then, a pure-Python
  structural validator (`scripts/validate_bundle.py`) checks the bundle in CI —
  expected targets and pipelines, per-target variables, production-mode
  `run_as`/branch pinning, and that every referenced notebook exists.
- **Branch-driven releases**: the workflow maps branches to environments —
  `main` → `prod`, `develop` → `qa`, feature branches → `dev` — and only deploys
  once workspace credentials are configured (the `deploy` step is gated on
  `DATABRICKS_HOST` being set).
- **Terraform stays infrastructure-only**: ADR-006 keeps Azure provisioning in
  Terraform; DABs own only the Databricks workspace resources, so ownership is
  clean.

## Expected Outcome

- **Reviewable releases** — a PR shows the pipeline definition diff; CI fails
  fast on structural defects without needing a live workspace.
- **Zero-drift environments** — catalogs and landing paths are declared once per
  target and cannot be retyped inconsistently.
- **Automatic, branch-scoped deployment** — merge to `main` releases to prod,
  merge to `develop` to qa, feature branches to dev, each gated on credentials.
- **Ready for Phase 5** — adding OIDC credentials to the workflow is a
  configuration change, not a redesign.

## Dependencies

- Databricks CLI `>= 0.231.0` (schema verified against `v1.10.0`); GitHub Action
  `databricks/setup-cli` provisions it in CI.
- The Lakeflow notebooks and manifests from Phase 3 (`notebooks/`, `pipelines/`).
- Unity Catalog schemas per environment (provisioned in Phase 2 by Terraform).
- Workspace credentials (`DATABRICKS_HOST` + `DATABRICKS_TOKEN`, or OIDC in
  Phase 5) before any real deployment runs.
- A service principal for production-mode pipelines (`run_as`) supplied via the
  `service_principal` variable.

## Implementation

- `bundle/databricks.yml` — the bundle: `variables` (`catalog`, `landing_path`,
  `service_principal`), `resources.pipelines` for Bronze/Silver/Gold, and
  `targets` `dev` (development mode) / `qa` / `prod` (production mode, pinned to
  `develop` and `main` respectively).
- `.github/workflows/dab-ci-cd.yml` — paths-filtered CI/CD: an offline
  structural validation job (always) and a workspace validation/deploy job
  (skipped until credentials are configured).
- `scripts/validate_bundle.py` — pure-Python (PyYAML) structural validator run
  in CI without Databricks credentials.
- The Lakeflow notebooks and manifests under `notebooks/` and `pipelines/` are the
  deployed artifacts the bundle references.

**Known consideration**: the Lakeflow notebooks import shared helpers from
`notebooks.shared` by climbing to the repository root. Once Phase 5 validates
the bundle against a real workspace, the pipeline `root_path` (or bundle layout)
may need adjustment so those imports resolve inside the deployed workspace.
