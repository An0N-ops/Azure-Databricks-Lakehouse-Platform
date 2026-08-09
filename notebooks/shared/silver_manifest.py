"""Silver ingestion manifests: loading, validation, and placeholder resolution.

Silver tables conform validated Bronze entities (ADR-005). A silver table spec
declares its Bronze source, primary/SCD keys, per-column conforming rules, and
DLT quality expectations. Like the Bronze manifest, templates carry
``{placeholder}`` tokens resolved from environment variables so one manifest
promotes unchanged across dev/qa/prod.

Validation is pure Python. When an ``entity_schema`` (entity -> column names)
is supplied it also verifies every referenced column exists, which the test
suite does by pinning the manifest to the synthetic generator pack.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import Any

from .bronze_manifest import (
    ManifestError,
    load_manifest,
    resolve_path,
)

SUPPORTED_CONFORM_RULES = frozenset({"trim", "lower", "upper", "initcap", "coalesce", "cast"})
SUPPORTED_CAST_TYPES = frozenset(
    {"string", "boolean", "integer", "long", "double", "date", "timestamp"}
)
SUPPORTED_SCD_TYPES = frozenset({1, 2})
DEFAULT_SCHEMA = "silver"

_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_KNOWN_PLACEHOLDERS = frozenset({"catalog", "landing", "schema", "table"})


def load_silver_manifest(path: str | Any) -> dict[str, Any]:
    """Load a Silver manifest JSON file into a dict."""
    return load_manifest(path)


def validate_silver_manifest(
    manifest: Mapping[str, Any], entity_schema: Mapping[str, Mapping[str, Any]] | None = None
) -> None:
    """Validate the structure of a Silver manifest, raising on any defect."""
    _require(manifest, "manifest must be an object")
    metadata = _require(manifest.get("metadata"), "metadata is required")
    pipeline = _require(metadata.get("pipeline"), "metadata.pipeline is required")
    if not isinstance(pipeline, str) or not pipeline.strip():
        raise ManifestError("metadata.pipeline must be a non-empty string")

    schema = manifest.get("schema", DEFAULT_SCHEMA)
    if not isinstance(schema, str) or not schema.strip():
        raise ManifestError("schema must be a non-empty string")
    _check_tokens(schema, context="schema")

    tables = _require(manifest.get("tables"), "tables is required")
    if not isinstance(tables, list) or not tables:
        raise ManifestError("tables must be a non-empty list")

    seen: set[str] = set()
    for index, table in enumerate(tables):
        _validate_table(table, index, seen, entity_schema)

    if "target" in manifest:
        target = manifest["target"]
        if not isinstance(target, str) or not target.strip():
            raise ManifestError("target must be a non-empty string")
        _check_tokens(target, context="target")


def _validate_table(
    table: Any,
    index: int,
    seen: set[str],
    entity_schema: Mapping[str, Mapping[str, Any]] | None,
) -> None:
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
    seen.add(name)

    source = _require(table.get("source"), f"tables[{index}].source is required")
    if not isinstance(source, Mapping):
        raise ManifestError(f"tables[{index}].source must be an object")
    source_table = _require(source.get("table"), f"tables[{index}].source.table is required")
    if not isinstance(source_table, str) or not source_table.strip():
        raise ManifestError(f"tables[{index}].source.table must be a non-empty string")
    _check_tokens(source_table, context=f"tables[{index}].source.table")

    primary_key = _require(table.get("primary_key"), f"tables[{index}].primary_key is required")
    if not isinstance(primary_key, str) or not primary_key.strip():
        raise ManifestError(f"tables[{index}].primary_key must be a non-empty string")

    keys = _require(table.get("keys"), f"tables[{index}].keys is required")
    if not isinstance(keys, list) or not keys or not all(isinstance(k, str) and k for k in keys):
        raise ManifestError(f"tables[{index}].keys must be a non-empty list of column names")

    scd_type = table.get("scd_type", 1)
    try:
        scd_type = int(scd_type)
    except (TypeError, ValueError):
        raise ManifestError(f"tables[{index}].scd_type must be 1 or 2")
    if scd_type not in SUPPORTED_SCD_TYPES:
        raise ManifestError(
            f"tables[{index}].scd_type '{scd_type}' is not supported "
            f"(expected one of {sorted(SUPPORTED_SCD_TYPES)})"
        )

    track_by = table.get("track_by")
    if scd_type == 2:
        if (
            not isinstance(track_by, list)
            or not track_by
            or not all(isinstance(col, str) and col for col in track_by)
        ):
            raise ManifestError(
                f"tables[{index}].track_by must be a non-empty list of column names "
                "when scd_type is 2"
            )
    elif track_by is not None:
        raise ManifestError(f"tables[{index}].track_by is only allowed with scd_type 2")

    conform = table.get("conform", {})
    if not isinstance(conform, Mapping):
        raise ManifestError(f"tables[{index}].conform must be an object")

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

    entity_columns = None
    if entity_schema is not None:
        entity_columns = entity_schema.get(name)
        if entity_columns is None:
            raise ManifestError(
                f"tables[{index}].name '{name}' has no matching entity in the provided schema"
            )
        if primary_key not in entity_columns:
            raise ManifestError(
                f"tables[{index}].primary_key '{primary_key}' is not a column of '{name}'"
            )
        for key in keys:
            if key not in entity_columns:
                raise ManifestError(
                    f"tables[{index}].keys entry '{key}' is not a column of '{name}'"
                )
        for column in track_by or []:
            if column not in entity_columns:
                raise ManifestError(
                    f"tables[{index}].track_by column '{column}' is not a column of '{name}'"
                )

    for column, rules in conform.items():
        if entity_columns is not None and column not in entity_columns:
            raise ManifestError(
                f"tables[{index}].conform references '{column}' which is not a column of '{name}'"
            )
        _validate_rules(column, rules, index)


def _validate_rules(column: str, rules: Any, index: int) -> None:
    if not isinstance(rules, list):
        raise ManifestError(f"tables[{index}].conform['{column}'] must be a list of rules")
    if not rules:
        raise ManifestError(f"tables[{index}].conform['{column}'] must not be empty")
    for rule in rules:
        if not isinstance(rule, Mapping):
            raise ManifestError(f"tables[{index}].conform['{column}'] rules must be objects")
        rule_name = _require(
            rule.get("rule"), f"tables[{index}].conform['{column}'] rule name is required"
        )
        if rule_name not in SUPPORTED_CONFORM_RULES:
            raise ManifestError(
                f"tables[{index}].conform['{column}'] rule '{rule_name}' is not supported "
                f"(expected one of {sorted(SUPPORTED_CONFORM_RULES)})"
            )
        if rule_name == "coalesce" and "value" not in rule:
            raise ManifestError(
                f"tables[{index}].conform['{column}'] coalesce rule requires 'value'"
            )
        if rule_name == "cast":
            cast_type = rule.get("type")
            if cast_type not in SUPPORTED_CAST_TYPES:
                raise ManifestError(
                    f"tables[{index}].conform['{column}'] cast rule type '{cast_type}' is "
                    f"not supported (expected one of {sorted(SUPPORTED_CAST_TYPES)})"
                )


def table_specs(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the Silver table specs, validated and deep-copied."""
    validate_silver_manifest(manifest)
    return [copy.deepcopy(table) for table in manifest.get("tables", [])]


def resolve_source_table(
    spec: Mapping[str, Any], variables: Mapping[str, str] | None = None
) -> str:
    """Resolve a spec's Bronze source table to a fully-qualified name."""
    return resolve_path(spec["source"]["table"], variables)


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
