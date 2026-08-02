"""Deterministic generation of all entities defined by an industry pack."""

from __future__ import annotations

import random
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date
from typing import Any

from sample_data.config import get_entity_volume, resolve_entity_order
from sample_data.errors import ConfigError
from sample_data.fields import build_generator, parse_field


@dataclass(frozen=True)
class Bounds:
    """The generation window shared by date/datetime fields without an override."""

    start: date
    end: date


def generate(
    config: dict[str, Any],
    seed: int = 42,
    start_date: str | None = None,
    end_date: str | None = None,
    scale: float = 1.0,
) -> OrderedDict[str, list[dict[str, Any]]]:
    """Generate every entity in ``config`` and return rows keyed by entity name.

    The result is deterministic: the same seed and configuration always produce
    identical rows. Each entity gets its own ``random.Random`` seeded with
    ``"{seed}:{entity}"`` so adding a field or entity does not perturb the rows
    of unrelated entities.
    """
    bounds = _resolve_bounds(config, start_date, end_date)
    order = resolve_entity_order(config)
    context: dict[str, list[dict[str, Any]]] = {}
    output: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for entity_name in order:
        rng = random.Random(f"{seed}:{entity_name}")
        volume = get_entity_volume(config, entity_name, scale=scale, context=context)
        rows = _generate_entity(
            entity_name, config["entities"][entity_name], rng, context, bounds, volume
        )
        context[entity_name] = rows
        output[entity_name] = rows
    return output


def _generate_entity(
    entity_name: str,
    entity: dict[str, Any],
    rng: random.Random,
    context: dict[str, list[dict[str, Any]]],
    bounds: Bounds,
    volume: int,
) -> list[dict[str, Any]]:
    field_specs = [parse_field(field, entity_name) for field in entity["fields"]]
    generators: list[Any] = []
    counters: dict[str, list[int]] = {}
    for spec in field_specs:
        if spec.kind == "id":
            prefix = spec.params["prefix"]
            padding = spec.params.get("padding", 6)
            counter = [1]
            counters[spec.name] = counter

            def make_id(
                _row: dict[str, Any], _prefix=prefix, _padding=padding, _counter=counter
            ) -> str:
                value = f"{_prefix}{_counter[0]:0{_padding}d}"
                _counter[0] += 1
                return value

            generators.append(make_id)
        else:
            generators.append(build_generator(spec, rng, context, bounds))

    rows: list[dict[str, Any]] = []
    for _ in range(volume):
        row: dict[str, Any] = {}
        for spec, generator in zip(field_specs, generators):
            row[spec.name] = generator(row)
        rows.append(row)
    return rows


def _resolve_bounds(config: dict[str, Any], start_date: str | None, end_date: str | None) -> Bounds:
    metadata = config.get("metadata", {})
    start = start_date or metadata.get("default_start_date")
    end = end_date or metadata.get("default_end_date")
    if not start or not end:
        raise ConfigError(
            "generation window is required: pass --start-date/--end-date or set "
            "'default_start_date'/'default_end_date' in the pack metadata"
        )
    try:
        start_obj = date.fromisoformat(start)
        end_obj = date.fromisoformat(end)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"invalid date '{start}'..'{end}' (expected YYYY-MM-DD)") from exc
    if start_obj > end_obj:
        raise ConfigError(f"start date '{start}' must not be after end date '{end}'")
    return Bounds(start=start_obj, end=end_obj)
