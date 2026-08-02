"""Bronze ingestion manifests: loading, validation, and placeholder resolution.

Manifests are the declarative source of truth for Bronze Auto Loader ingestion
(see ADR-004). Each table spec describes a raw landing source and the Delta
Live Tables table it should populate. Paths and target names carry
``{placeholder}`` tokens that are resolved from environment variables, so a
single manifest can be promoted from dev to qa to prod unchanged.

This module is intentionally pure Python (no PySpark imports) so manifests can
be loaded, validated, and unit-tested outside a Databricks runtime.
"""

from __future__ import annotations

import copy
import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_KNOWN_PLACEHOLDERS = frozenset({"catalog", "landing", "schema", "table"})
_SUPPORTED_FORMATS = frozenset({"csv", "json", "parquet"})
_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

DEFAULT_CATALOG = "dev_lakehouse"
DEFAULT_SCHEMA = "bronze"
DEFAULT_TARGET = "{catalog}.{schema}.{table}"

CATALOG_ENV = "DATABRICKS_CATALOG"
LANDING_ENV = "DATABRICKS_LANDING_PATH"


class ManifestError(Exception):
    """Raised when a Bronze manifest is missing, malformed, or invalid."""


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Load a manifest JSON file into a dict.

    Raises :class:`ManifestError` if the file is missing or not valid JSON.
    """
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise ManifestError(f"manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"manifest is not valid JSON: {manifest_path}") from exc
    return manifest


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    """Validate the structure of a Bronze manifest, raising on any defect."""
    _require(manifest, "manifest must be an object")
    metadata = _require(manifest.get("metadata"), "metadata is required")
    pipeline = _require(metadata.get("pipeline"), "metadata.pipeline is required")
    if not isinstance(pipeline, str) or not pipeline.strip():
        raise ManifestError("metadata.pipeline must be a non-empty string")

    tables = _require(manifest.get("tables"), "tables is required")
    if not isinstance(tables, list) or not tables:
        raise ManifestError("tables must be a non-empty list")

    schema = manifest.get("schema", DEFAULT_SCHEMA)
    if not isinstance(schema, str) or not schema.strip():
        raise ManifestError("schema must be a non-empty string")
    _check_tokens(schema, context="schema")

    defaults = manifest.get("defaults", {})
    if not isinstance(defaults, Mapping):
        raise ManifestError("defaults must be an object")

    default_format = (
        (defaults.get("source") or {}).get("format")
        if isinstance(defaults.get("source"), Mapping)
        else None
    )
    if default_format is not None and default_format not in _SUPPORTED_FORMATS:
        raise ManifestError(
            f"defaults.source.format '{default_format}' is not supported "
            f"(expected one of {sorted(_SUPPORTED_FORMATS)})"
        )

    seen: set[str] = set()
    for index, table in enumerate(tables):
        _validate_table(table, index, default_format, seen)
        name = table["name"]
        if name in seen:
            raise ManifestError(f"duplicate table name: {name}")
        seen.add(name)

    if "target" in manifest:
        target = manifest["target"]
        if not isinstance(target, str) or not target.strip():
            raise ManifestError("target must be a non-empty string")
        _check_tokens(target, context="target")


def _validate_table(table: Any, index: int, default_format: str | None, seen: set[str]) -> None:
    if not isinstance(table, Mapping):
        raise ManifestError(f"tables[{index}] must be an object")

    name = _require(table.get("name"), f"tables[{index}].name is required")
    if not isinstance(name, str) or not _TABLE_NAME_RE.match(name):
        raise ManifestError(
            f"tables[{index}].name '{name}' is not a valid table name "
            "(alphanumeric/underscore, starting with a letter or underscore)"
        )
    if name in seen:
        raise ManifestError(f"duplicate table name: {name}")

    primary_key = _require(table.get("primary_key"), f"tables[{index}].primary_key is required")
    if not isinstance(primary_key, str) or not primary_key.strip():
        raise ManifestError(f"tables[{index}].primary_key must be a non-empty string")

    source = _require(table.get("source"), f"tables[{index}].source is required")
    if not isinstance(source, Mapping):
        raise ManifestError(f"tables[{index}].source must be an object")
    path = _require(source.get("path"), f"tables[{index}].source.path is required")
    if not isinstance(path, str) or not path.strip():
        raise ManifestError(f"tables[{index}].source.path must be a non-empty string")
    _check_tokens(path, context=f"tables[{index}].source.path")

    fmt = source.get("format", default_format)
    if fmt is None:
        raise ManifestError(
            f"tables[{index}].source.format is required (no defaults.source.format configured)"
        )
    if fmt not in _SUPPORTED_FORMATS:
        raise ManifestError(
            f"tables[{index}].source.format '{fmt}' is not supported "
            f"(expected one of {sorted(_SUPPORTED_FORMATS)})"
        )

    options = source.get("options")
    if options is not None and not isinstance(options, Mapping):
        raise ManifestError(f"tables[{index}].source.options must be an object")

    expectations = table.get("expectations", [])
    if not isinstance(expectations, list):
        raise ManifestError(f"tables[{index}].expectations must be a list")
    expectation_names: set[str] = set()
    for expectation_index, expectation in enumerate(expectations):
        if not isinstance(expectation, Mapping):
            raise ManifestError(
                f"tables[{index}].expectations[{expectation_index}] must be an object"
            )
        exp_name = expectation.get("name")
        constraint = expectation.get("constraint")
        if not isinstance(exp_name, str) or not exp_name.strip():
            raise ManifestError(
                f"tables[{index}].expectations[{expectation_index}].name must be a non-empty string"
            )
        if not isinstance(constraint, str) or not constraint.strip():
            raise ManifestError(
                f"tables[{index}].expectations[{expectation_index}].constraint must be a "
                "non-empty string"
            )
        if exp_name in expectation_names:
            raise ManifestError(f"tables[{index}].expectations has duplicate name '{exp_name}'")
        expectation_names.add(exp_name)


def table_specs(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the effective table specs with ``defaults.source`` merged in."""
    validate_manifest(manifest)
    defaults = manifest.get("defaults", {})
    default_source = defaults.get("source", {}) if isinstance(defaults, Mapping) else {}
    specs: list[dict[str, Any]] = []
    for table in manifest.get("tables", []):
        spec = copy.deepcopy(table)
        merged_source = dict(default_source)
        merged_source.update(spec.get("source", {}))
        spec["source"] = merged_source
        specs.append(spec)
    return specs


def default_variables() -> dict[str, str]:
    """Resolve environment-driven placeholder values.

    ``catalog`` falls back to ``dev_lakehouse``; ``landing`` is only present
    when ``DATABRICKS_LANDING_PATH`` is set. A source path that references
    ``{landing}`` without the environment variable fails at resolution time.
    """
    variables = {"catalog": os.environ.get(CATALOG_ENV, DEFAULT_CATALOG)}
    landing = os.environ.get(LANDING_ENV)
    if landing:
        variables["landing"] = landing.rstrip("/")
    return variables


def resolve_path(template: str, variables: Mapping[str, str] | None = None) -> str:
    """Substitute ``{placeholder}`` tokens in ``template``.

    Explicit ``variables`` override environment-driven defaults. Unknown
    tokens or tokens without a value raise :class:`ManifestError`.
    """
    merged = default_variables()
    merged.update(variables or {})
    resolved = _PLACEHOLDER_RE.sub(lambda match: _token_value(match, template, merged), template)
    if "{" in resolved or "}" in resolved:
        raise ManifestError(f"unresolved placeholder in '{template}'")
    return resolved


def _token_value(match: re.Match, template: str, variables: Mapping[str, str]) -> str:
    key = match.group(1)
    value = variables.get(key)
    if value is None or value == "":
        raise ManifestError(
            f"no value for placeholder '{{{key}}}' in '{template}' "
            f"(set {LANDING_ENV} or pass it in variables)"
        )
    return value


def resolve_source_path(spec: Mapping[str, Any], variables: Mapping[str, str] | None = None) -> str:
    """Resolve a table spec's landing source path to an absolute location."""
    return resolve_path(spec["source"]["path"], variables)


def target_table_name(
    manifest: Mapping[str, Any],
    spec: Mapping[str, Any],
    variables: Mapping[str, str] | None = None,
) -> str:
    """Resolve the fully-qualified Unity Catalog target for a table spec."""
    template = manifest.get("target", DEFAULT_TARGET)
    merged = default_variables()
    merged.update(variables or {})
    merged["schema"] = manifest.get("schema", DEFAULT_SCHEMA)
    merged["table"] = spec["name"]
    return resolve_path(template, merged)


def _require(value: Any, message: str) -> Any:
    if value is None:
        raise ManifestError(message)
    return value


def _check_tokens(text: str, *, context: str) -> None:
    for match in _PLACEHOLDER_RE.finditer(text):
        if match.group(1) not in _KNOWN_PLACEHOLDERS:
            raise ManifestError(
                f"{context} references unknown placeholder '{{{match.group(1)}}}' "
                f"(known: {sorted(_KNOWN_PLACEHOLDERS)})"
            )
