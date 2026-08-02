## Description

Provide a clear and concise summary of the changes proposed in this Pull Request. Include relevant context, business rationale, and architectural implications.

Fixes / Implements: #(issue number)

---

## Type of Change

- [ ] **Feature**: New pipeline, notebook, or data framework capability.
- [ ] **Infrastructure**: New or updated Terraform HCL module / environment config.
- [ ] **Bug Fix**: Fix for an existing issue or failing test.
- [ ] **Refactoring**: Code optimization without changing external interfaces.
- [ ] **Documentation**: Architectural, deployment, or operational doc updates.
- [ ] **CI/CD**: Workflows, GitHub Actions, or dependency updates.

---

## Verification & Testing

### 1. Automated Verification
- [ ] Terraform modules validated (`terraform validate` & `terraform fmt -check`).
- [ ] Python scripts / notebooks formatted and linted (`ruff check .`).
- [ ] YAML & Markdown syntax validated.

### 2. Manual Verification Evidence
Provide exact command outputs, log snippets, or visual screenshots confirming successful execution.

```text
[Insert verification logs or execution outputs here]
```

---

## Security & Compliance Checklist

- [ ] **No Hardcoded Secrets**: Scanned for API keys, passwords, or connection strings.
- [ ] **Unity Catalog Compliance**: Table & schema access adheres to explicit 3-level namespace RBAC rules.
- [ ] **Encryption & Storage**: TLS 1.2+ and ADLS Gen2 Hierarchical Namespace rules enforced.
- [ ] **Code Owners Review**: Tagged appropriate component maintainers.
