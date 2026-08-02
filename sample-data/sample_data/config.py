"""Configuration loading and validation for industry data packs.

An industry pack is a directory containing ``config.json`` that declares the
entities, fields, and volumes the generator should produce. This module is
responsible for loading that file and failing fast with actionable messages
when the pack is malformed or internally inconsistent.
"""

from __future__ import annotations

import json
import random
import string
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from sample_data.errors import ConfigError
from sample_data.fields import build_generator, parse_field

SUPPORTED_FIELD_TYPES = frozenset(
    {
        "id",
        "choice",
        "int_range",
        "float_range",
        "date_between",
        "datetime_between",
        "string_pattern",
        "constant",
        "foreign_key",
        "expression",
        "conditional",
    }
)


def load_config(path: Path) -> dict[str, Any]:
    """Load and validate an industry pack configuration from ``path``."""
    if not Path(path).is_file():
        raise ConfigError(f"industry pack not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(config, dict):
        raise ConfigError(f"{path}: config root must be a JSON object")
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    """Validate the structure and internal consistency of ``config``."""
    metadata = config.get("metadata")
    if not isinstance(metadata, dict):
        raise ConfigError("config: missing 'metadata' object")
    for key in ("industry", "company"):
        if not isinstance(metadata.get(key), str) or not metadata[key]:
            raise ConfigError(f"config metadata: '{key}' is required")

    entities = config.get("entities")
    if not isinstance(entities, dict) or not entities:
        raise ConfigError("config: 'entities' must be a non-empty object")

    names: dict[str, list[str]] = {}
    for name, entity in entities.items():
        if not isinstance(entity, dict):
            raise ConfigError(f"{name}: entity must be an object")
        fields = entity.get("fields")
        if not isinstance(fields, list) or not fields:
            raise ConfigError(f"{name}: 'fields' must be a non-empty list")
        _validate_entity_volume(name, entity.get("volume"))

        field_names: list[str] = []
        seen = set()
        for field in fields:
            if not isinstance(field, dict):
                raise ConfigError(f"{name}: each field must be an object")
            field_name = field.get("name")
            if not isinstance(field_name, str) or not field_name:
                raise ConfigError(f"{name}: each field requires a string 'name'")
            if field_name in seen:
                raise ConfigError(f"{name}: duplicate field '{field_name}'")
            seen.add(field_name)
            field_names.append(field_name)
            if field.get("type") not in SUPPORTED_FIELD_TYPES:
                raise ConfigError(
                    f"{name}.{field_name}: unsupported field type '{field.get('type')}'"
                )
        names[name] = field_names

    for name, entity in entities.items():
        field_names = names[name]
        for index, field in enumerate(entity["fields"]):
            spec = parse_field(field, name)
            _validate_field(spec, name, field_names[:index], names, _validation_bounds(metadata))

    resolve_entity_order(config)


def _validate_entity_volume(name: str, volume: Any) -> None:
    if isinstance(volume, int):
        if volume < 0:
            raise ConfigError(f"{name}: 'volume' cannot be negative")
        return
    if isinstance(volume, dict):
        ref = volume.get("rows_per_reference")
        per = volume.get("rows_per_unit")
        if isinstance(ref, str) and ref and isinstance(per, (int, float)) and per > 0:
            return
        raise ConfigError(
            f"{name}: reference volume needs 'rows_per_reference' (entity) "
            "and 'rows_per_unit' (number > 0)"
        )
    raise ConfigError(
        f"{name}: 'volume' must be an int or {{'rows_per_reference', 'rows_per_unit'}}"
    )


def _validation_bounds(metadata: dict[str, Any]):
    """A fallback generation window so window-less date fields validate."""
    try:
        start = date.fromisoformat(metadata.get("default_start_date", "2000-01-01"))
        end = date.fromisoformat(metadata.get("default_end_date", "2030-01-01"))
    except (TypeError, ValueError):
        start, end = None, None
    return SimpleNamespace(start=start, end=end)


def _validate_field(
    spec: Any,
    entity_name: str,
    earlier: list[str],
    names: dict[str, list[str]],
    bounds,
) -> None:
    """Validate one field, including cross-entity references."""
    kind = spec.kind
    params = spec.params
    if kind == "id":
        if not isinstance(params.get("prefix"), str) or not params["prefix"]:
            raise ConfigError(f"{entity_name}.{spec.name}: 'id' requires a 'prefix'")
        padding = params.get("padding", 6)
        if not isinstance(padding, int) or padding < 1:
            raise ConfigError(f"{entity_name}.{spec.name}: 'padding' must be a positive int")
    elif kind == "foreign_key":
        ref = params.get("entity")
        column = params.get("column")
        if ref not in names:
            raise ConfigError(f"{entity_name}.{spec.name}: unknown foreign key entity '{ref}'")
        if column not in names[ref]:
            raise ConfigError(f"{entity_name}.{spec.name}: '{ref}' has no column '{column}'")
        build_generator(spec, random.Random(0), {}, bounds)
    elif kind == "conditional":
        condition = params.get("field")
        if condition not in earlier:
            raise ConfigError(
                f"{entity_name}.{spec.name}: condition field '{condition}' "
                "must appear earlier in the entity"
            )
        cases = params.get("cases")
        if not isinstance(cases, list) or not cases:
            raise ConfigError(f"{entity_name}.{spec.name}: 'conditional' needs 'cases'")
        for case in cases:
            sub_dict = case.get("spec")
            if not isinstance(sub_dict, dict):
                raise ConfigError(f"{entity_name}.{spec.name}: each case requires a 'spec' object")
            sub = parse_field(dict(sub_dict, name=spec.name), entity_name)
            _validate_field(sub, entity_name, earlier, names, bounds)
        if params.get("default") is not None:
            default_dict = params["default"]
            if not isinstance(default_dict, dict):
                raise ConfigError(
                    f"{entity_name}.{spec.name}: 'default' must be a field spec object"
                )
            sub = parse_field(dict(default_dict, name=spec.name), entity_name)
            _validate_field(sub, entity_name, earlier, names, bounds)
    elif kind == "expression":
        template = params.get("template")
        if not isinstance(template, str) or not template:
            raise ConfigError(f"{entity_name}.{spec.name}: 'expression' needs 'template'")
        for _, field_name, _, _ in string.Formatter().parse(template):
            if field_name and field_name not in earlier:
                raise ConfigError(
                    f"{entity_name}.{spec.name}: template references '{field_name}' "
                    "which must appear earlier in the entity"
                )
        build_generator(spec, random.Random(0), {}, bounds)
    else:
        build_generator(spec, random.Random(0), {}, bounds)


def resolve_entity_order(config: dict[str, Any]) -> list[str]:
    """Return entity names in dependency order (foreign keys first)."""
    entities = config["entities"]
    deps: dict[str, set] = {}
    for name, entity in entities.items():
        required = set()
        for field in entity["fields"]:
            for inner in _iter_specs(field):
                if inner.get("type") == "foreign_key":
                    ref = inner.get("entity")
                    if isinstance(ref, str):
                        required.add(ref)
        volume = entity.get("volume")
        if isinstance(volume, dict):
            ref = volume.get("rows_per_reference")
            if isinstance(ref, str):
                required.add(ref)
        deps[name] = required

    for name, required in deps.items():
        for ref in required:
            if ref not in entities:
                raise ConfigError(f"{name}: depends on unknown entity '{ref}'")

    ordered: list[str] = []
    resolved: set = set()
    while len(ordered) < len(deps):
        progress = False
        for name, required in deps.items():
            if name in resolved:
                continue
            if required <= resolved:
                resolved.add(name)
                ordered.append(name)
                progress = True
        if not progress:
            cycle = [n for n in deps if n not in resolved]
            raise ConfigError(f"dependency cycle detected among: {', '.join(sorted(cycle))}")
    return ordered


def _iter_specs(field: dict[str, Any]):
    """Yield ``field`` and every nested spec inside a conditional field."""
    yield field
    if field.get("type") == "conditional":
        for case in field.get("cases", []):
            spec = case.get("spec")
            if isinstance(spec, dict):
                yield from _iter_specs(spec)
        default = field.get("default")
        if isinstance(default, dict):
            yield from _iter_specs(default)


def get_entity_volume(
    config: dict[str, Any],
    entity_name: str,
    scale: float,
    context: dict[str, list[dict[str, Any]]] | None,
) -> int:
    """Compute the number of rows for ``entity_name``, applying ``scale``."""
    volume = config["entities"][entity_name]["volume"]
    if isinstance(volume, int):
        base = volume
    else:
        ref = volume["rows_per_reference"]
        per = volume["rows_per_unit"]
        reference_rows = len((context or {}).get(ref, []))
        base = reference_rows * per
    return max(1, round(base * scale))
