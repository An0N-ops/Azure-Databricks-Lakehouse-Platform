"""Offline structural validation for the Databricks Asset Bundle.

``databricks bundle validate`` requires a live workspace connection, which is
not available until Phase 5 wires up OIDC credentials in CI. This module runs
the checks that can be made from the repository alone:

- the bundle declares the expected environments, the medallion pipeline, and
  the synthetic data-generation job,
- the pipeline references notebook globs that match files on disk,
- the pipeline exposes the manifest placeholders (catalog, landing path) via
  ``configuration`` (the serverless-safe replacement for cluster
  ``spark_env_vars``),
- the job runs the data-generation notebook with catalog/landing parameters,
  and
- production targets are pinned to a git branch and a service principal.

It is pure Python (PyYAML) so it runs in CI without Databricks credentials,
mirroring the offline manifest validators under ``notebooks/shared``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

EXPECTED_TARGETS = ("dev", "qa", "prod")
PIPELINE_NAME = "energy_lakehouse"
PIPELINE_NOTEBOOK_GLOBS = (
    "notebooks/bronze/**",
    "notebooks/silver/**",
    "notebooks/gold/**",
)
REQUIRED_CONFIG = ("DATABRICKS_CATALOG", "DATABRICKS_LANDING_PATH")
JOB_NAME = "generate_energy_data"
JOB_NOTEBOOK = "notebooks/generate_energy_data.py"
JOB_PARAMS = ("catalog", "landing_path")


class BundleError(Exception):
    """Raised when the bundle configuration is structurally invalid."""


def load_bundle(root: Path) -> dict:
    """Load ``bundle/databricks.yml`` from ``root`` as a dict."""
    config_path = root / "bundle" / "databricks.yml"
    if not config_path.is_file():
        raise BundleError(f"bundle config not found: {config_path}")
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise BundleError(f"bundle config is not valid YAML: {config_path}") from exc
    if not isinstance(config, dict):
        raise BundleError("bundle config must be a mapping")
    return config


def _require(value, message: str):
    if not value:
        raise BundleError(message)
    return value


def _require_mapping(value, message: str) -> dict:
    if not isinstance(value, dict):
        raise BundleError(message)
    return value


def validate_bundle(config: dict, root: Path) -> None:
    """Validate the bundle structure, raising :class:`BundleError` on any defect."""
    bundle = _require_mapping(config.get("bundle"), "bundle is required")
    name = _require(bundle.get("name"), "bundle.name is required")
    if not isinstance(name, str) or not name.strip():
        raise BundleError("bundle.name must be a non-empty string")
    if "databricks_cli_version" not in bundle:
        raise BundleError("bundle.databricks_cli_version is required")

    variables = _require_mapping(config.get("variables"), "variables is required")
    for variable in ("catalog", "landing_path"):
        if variable not in variables:
            raise BundleError(f"variables.{variable} is required")

    resources = _require_mapping(config.get("resources"), "resources is required")

    pipelines = _require_mapping(resources.get("pipelines"), "resources.pipelines is required")
    if PIPELINE_NAME not in pipelines:
        raise BundleError(f"resources.pipelines.{PIPELINE_NAME} is required")
    _validate_pipeline(PIPELINE_NAME, _require_mapping(pipelines[PIPELINE_NAME], "pipeline"), root)

    jobs = _require_mapping(resources.get("jobs"), "resources.jobs is required")
    if JOB_NAME not in jobs:
        raise BundleError(f"resources.jobs.{JOB_NAME} is required")
    _validate_job(JOB_NAME, _require_mapping(jobs[JOB_NAME], "job"), root)

    targets = _require_mapping(config.get("targets"), "targets is required")
    for expected in EXPECTED_TARGETS:
        _validate_target(
            expected, _require_mapping(targets.get(expected), f"targets.{expected} is required")
        )


def _validate_pipeline(name: str, pipeline: dict, root: Path) -> None:
    if pipeline.get("name") != name:
        raise BundleError(f"resources.pipelines.{name}.name must equal '{name}'")
    if not pipeline.get("catalog"):
        raise BundleError(f"resources.pipelines.{name}.catalog is required")

    configuration = _require_mapping(
        pipeline.get("configuration"),
        f"resources.pipelines.{name}.configuration is required",
    )
    for variable in REQUIRED_CONFIG:
        if variable not in configuration:
            raise BundleError(f"resources.pipelines.{name}.configuration.{variable} is required")

    libraries = pipeline.get("libraries")
    if not isinstance(libraries, list) or not libraries:
        raise BundleError(f"resources.pipelines.{name}.libraries must be a non-empty list")
    glob_paths = []
    for library in libraries:
        library = _require_mapping(
            library, f"resources.pipelines.{name}.libraries entries must be mappings"
        )
        library_glob = _require_mapping(
            library.get("glob"),
            f"resources.pipelines.{name}.libraries[].glob is required",
        )
        include = _require(
            library_glob.get("include"), "resources.pipelines.[].glob.include is required"
        )
        glob_paths.append(include.lstrip("./"))

    for expected_glob in PIPELINE_NOTEBOOK_GLOBS:
        if expected_glob not in glob_paths:
            raise BundleError(
                f"resources.pipelines.{name} must reference '{expected_glob}' in libraries"
            )
    for glob_path in glob_paths:
        matches = list(root.glob(glob_path))
        if not matches:
            raise BundleError(
                f"resources.pipelines.{name} references glob with no matches: {glob_path}"
            )


def _validate_job(name: str, job: dict, root: Path) -> None:
    tasks = job.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise BundleError(f"resources.jobs.{name}.tasks must be a non-empty list")
    task_keys = []
    for task in tasks:
        notebook_task = _require_mapping(
            task.get("notebook_task"),
            f"resources.jobs.{name}.tasks[].notebook_task is required",
        )
        notebook_path = _require(
            notebook_task.get("notebook_path"),
            f"resources.jobs.{name}.tasks[].notebook_task.notebook_path is required",
        )
        if notebook_path.lstrip("./") != JOB_NOTEBOOK:
            raise BundleError(
                f"resources.jobs.{name} must reference {JOB_NOTEBOOK} in notebook_task"
            )
        if not (root / notebook_path.lstrip("./")).is_file():
            raise BundleError(f"resources.jobs.{name} references missing notebook: {notebook_path}")
        base_parameters = _require_mapping(
            notebook_task.get("base_parameters"),
            f"resources.jobs.{name}.tasks[].notebook_task.base_parameters is required",
        )
        for parameter in JOB_PARAMS:
            if parameter not in base_parameters:
                raise BundleError(
                    f"resources.jobs.{name}.tasks[].notebook_task.base_parameters.{parameter} "
                    "is required"
                )
        task_keys.append(task.get("task_key"))

    if not task_keys or any(key is None for key in task_keys):
        raise BundleError(f"resources.jobs.{name}.tasks[].task_key is required")


def _validate_target(name: str, target: dict) -> None:
    workspace = _require_mapping(target.get("workspace"), f"targets.{name}.workspace is required")
    host = _require(workspace.get("host"), f"targets.{name}.workspace.host is required")
    if not isinstance(host, str) or not host.strip():
        raise BundleError(f"targets.{name}.workspace.host must be a non-empty string")

    target_variables = _require_mapping(
        target.get("variables"), f"targets.{name}.variables is required"
    )
    for variable in ("catalog", "landing_path"):
        value = target_variables.get(variable)
        if not isinstance(value, str) or not value.strip():
            raise BundleError(f"targets.{name}.variables.{variable} must be a non-empty string")

    if name == "dev":
        if target.get("mode") != "development":
            raise BundleError("targets.dev.mode must be 'development'")
    else:
        if target.get("mode") != "production":
            raise BundleError(f"targets.{name}.mode must be 'production'")
        git = _require_mapping(
            target.get("git"), f"targets.{name}.git is required for production mode"
        )
        if not git.get("branch"):
            raise BundleError(f"targets.{name}.git.branch is required for production mode")
        run_as = _require_mapping(
            target.get("run_as"), f"targets.{name}.run_as is required for production mode"
        )
        if not run_as.get("service_principal_name"):
            raise BundleError(
                f"targets.{name}.run_as.service_principal_name is required for production mode"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle", type=Path, default=Path("."), help="Repository root containing bundle/."
    )
    args = parser.parse_args(argv)

    try:
        config = load_bundle(args.bundle)
        validate_bundle(config, args.bundle)
    except BundleError as exc:
        print(f"bundle validation failed: {exc}", file=sys.stderr)
        return 1
    print("bundle validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
