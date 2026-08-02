# Contributing Guidelines

Thank you for contributing to the **Azure Databricks Lakehouse Platform**. This repository adheres to enterprise software engineering standards. Every contribution must meet high quality, security, and architectural criteria.

---

## Code of Conduct

All contributors are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to the project maintainers.

---

## Development Workflow & Git Standards

### 1. Branching Strategy

We follow a trunk-based model:

```text
main ──────────────────●────────────────── (Protected, Production-Ready)
                       │
                       ▲
feat/unity-catalog     └───●───●           (Topic Branch)
```

- `main`: Production-ready baseline code. Protected branch; direct pushes are disabled. All work lands via pull requests.
- `feat/<area>`: Topic branches for new capabilities (e.g., `feat/unity-catalog-grants`, `feat/dlt-silver-pipelines`).
- `fix/<area>`: Bug-fix branches for verified issues.
- `docs/<area>`: Documentation-only changes (e.g., `docs/adr`).
- `chore/<area>`: Maintenance tasks, dependency updates, CI/CD changes.

Branch names use lowercase with a `/` between type and area. Keep branches short-lived and merge via pull request.

### 2. Conventional Commit Messages

Commit messages must conform to the [Conventional Commits specification](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]
```

**Allowed Types:**
- `feat`: A new feature or pipeline capability (e.g., `feat(dlt): implement oracle fusion erp bronze ingestion pipeline`)
- `fix`: A bug fix (e.g., `fix(terraform): resolve key vault access policy race condition`)
- `docs`: Documentation updates (e.g., `docs(architecture): expand unity catalog governance specification`)
- `style`: Code formatting, missing semi-colons, etc. (no code logic change)
- `refactor`: Code restructuring without functional behavior changes
- `test`: Adding or refactoring unit/integration tests
- `chore`: Maintenance tasks, dependency updates, CI workflow edits

### 3. Pre-commit Hooks

Local hooks enforce the same checks as CI so every commit already passes:

```bash
pip install pre-commit
pre-commit install
```

Run against all files on demand:

```bash
pre-commit run --all-files
```

The configuration in `.pre-commit-config.yaml` runs: whitespace/EOF fixes, merge-conflict and private-key detection, a large-file guard, Ruff (lint + format), markdownlint-cli2, yamllint, Gitleaks, and `terraform fmt`. `terraform validate` requires Azure credentials and is intentionally excluded from hooks; run it manually before opening a pull request.

---

## Code Quality Standards

### Python & PySpark
- **Formatter**: [Ruff](https://github.com/astral-sh/ruff) (or Black / Flake8 compatibility).
- **Type Annotations**: Mandatory for shared helper functions and core framework code.
- **Docstrings**: Google Style Python docstrings for all modules, classes, and public functions.
- **Spark Optimization**: Avoid `.collect()` on non-driver datasets. Prefer vectorized PySpark expressions and Delta Lake MERGE statements.

### Terraform & HCL
- **Formatter**: Standard `terraform fmt -recursive`.
- **Validation**: All modules must pass `terraform validate`. `tflint` is planned for CI in Phase 5.
- **Modularity**: Every module must include explicit `main.tf`, `variables.tf` (with descriptions and types), and `outputs.tf`.

### Documentation
- Use GitHub Flavored Markdown.
- Ensure all relative file links (`[file](file:///...)` or standard markdown links) are valid.
- Maintain a clean heading hierarchy (`#`, `##`, `###`).

---

## Pull Request Process

1. **Fork & Branch**: Create your topic branch from `main`.
2. **Local Verification**:
   - Run linter / formatting checks.
   - Run Terraform validation.
3. **Submit PR**: Open a Pull Request using the [PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).
4. **CI Checks**: Ensure all GitHub Actions checks pass (Markdown, YAML, Python, Terraform, Secret Scanning, Conventional Commits).
5. **Code Review**: Obtain approval from at least 1 designated code owner listed in `.github/CODEOWNERS`.
