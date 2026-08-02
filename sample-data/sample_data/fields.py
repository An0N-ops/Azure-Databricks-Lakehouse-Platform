"""Field generator primitives.

Each field in an industry pack maps to a generator built here. Generators are
pure functions of a seeded ``random.Random`` instance plus previously generated
data, which keeps output deterministic for a given seed and configuration.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Callable  # noqa: UP035

from sample_data.errors import ConfigError

_UPPER = string.ascii_uppercase
_DIGITS = string.digits

# A generator produces a value for one field of one row. It receives the
# partially-built row so expression/conditional fields can read earlier fields.
Generator = Callable[[Any], Any]


class FieldTypeError(ConfigError):
    """Raised when a field spec is invalid for its declared type."""


@dataclass(frozen=True)
class FieldSpec:
    name: str
    kind: str
    params: dict[str, Any]


def parse_field(spec: dict[str, Any], entity_name: str) -> FieldSpec:
    """Split a field dict into a ``FieldSpec`` and validate the bare essentials."""
    name = spec.get("name")
    kind = spec.get("type")
    if not isinstance(name, str) or not name:
        raise ConfigError(f"{entity_name}: field missing a string 'name'")
    if not isinstance(kind, str) or not kind:
        raise ConfigError(f"{entity_name}.{name}: missing 'type'")
    params = {key: value for key, value in spec.items() if key not in ("name", "type")}
    return FieldSpec(name=name, kind=kind, params=params)


def build_generator(
    spec: FieldSpec,
    rng: random.Random,
    context: dict[str, list[dict[str, Any]]],
    bounds: Any | None = None,
) -> Generator:
    """Build a generator for ``spec``. Errors indicate a misconfigured pack."""
    kind = spec.kind
    params = spec.params
    name = spec.name

    if kind == "choice":
        values = params.get("values")
        if not isinstance(values, list) or not values:
            raise FieldTypeError(f"{name}: 'choice' requires a non-empty 'values' list")
        weights = params.get("weights")
        if weights is not None:
            if not isinstance(weights, list) or len(weights) != len(values):
                raise FieldTypeError(f"{name}: 'weights' must match 'values' length")
            return lambda _row: rng.choices(values, weights=weights, k=1)[0]
        return lambda _row: rng.choice(values)

    if kind == "int_range":
        lo, hi = _range_params(spec)
        return lambda _row: rng.randint(lo, hi)

    if kind == "float_range":
        lo, hi = _range_params(spec)
        digits = params.get("round")
        if digits is not None and (not isinstance(digits, int) or digits < 0):
            raise FieldTypeError(f"{name}: 'round' must be a non-negative int or omitted")
        if digits is None:
            return lambda _row: rng.uniform(lo, hi)
        return lambda _row: round(rng.uniform(lo, hi), digits)

    if kind == "date_between":
        start, end, fmt = _date_params(spec, bounds, "date")
        lo, hi = start.toordinal(), end.toordinal()
        return lambda _row: date.fromordinal(rng.randint(lo, hi)).strftime(fmt)

    if kind == "datetime_between":
        start, end, fmt = _date_params(spec, bounds, "datetime")
        lo, hi = _to_seconds(start), _to_seconds(end)
        return lambda _row: _from_seconds(rng.randint(lo, hi)).strftime(fmt)

    if kind == "string_pattern":
        pattern = params.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise FieldTypeError(f"{name}: 'string_pattern' requires a 'pattern'")
        return lambda _row: _expand_pattern(pattern, rng)

    if kind == "constant":
        if "value" not in params:
            raise FieldTypeError(f"{name}: 'constant' requires a 'value'")
        value = params["value"]
        return lambda _row: value

    if kind == "foreign_key":
        ref_entity = params.get("entity")
        ref_column = params.get("column")
        if not isinstance(ref_entity, str) or not ref_entity:
            raise FieldTypeError(f"{name}: 'foreign_key' requires an 'entity'")
        if not isinstance(ref_column, str) or not ref_column:
            raise FieldTypeError(f"{name}: 'foreign_key' requires a 'column'")
        null_pct = params.get("null_pct", 0.0)
        if not isinstance(null_pct, (int, float)) or not 0 <= null_pct <= 1:
            raise FieldTypeError(f"{name}: 'null_pct' must be between 0 and 1")

        def _foreign_key(_row: dict[str, Any]) -> Any:
            ref_rows = context.get(ref_entity) or []
            if not ref_rows:
                return None
            if null_pct and rng.random() < null_pct:
                return None
            return rng.choice(ref_rows)[ref_column]

        return _foreign_key

    if kind == "expression":
        template = params.get("template")
        if not isinstance(template, str) or not template:
            raise FieldTypeError(f"{name}: 'expression' requires a 'template'")

        def _expression(row: dict[str, Any]) -> str:
            try:
                return template.format(**row)
            except (KeyError, ValueError, IndexError) as exc:
                raise FieldTypeError(f"{name}: expression template failed: {exc}") from exc

        return _expression

    if kind == "conditional":
        condition = params.get("field")
        if not isinstance(condition, str) or not condition:
            raise FieldTypeError(f"{name}: 'conditional' requires a 'field'")
        cases = params.get("cases")
        if not isinstance(cases, list) or not cases:
            raise FieldTypeError(f"{name}: 'conditional' requires a 'cases' list")

        case_factories: list[tuple] = []
        for case in cases:
            when = case.get("when")
            sub_dict = case.get("spec")
            if not isinstance(sub_dict, dict):
                raise FieldTypeError(f"{name}: each case requires a 'spec' object")
            sub_spec = FieldSpec(name=name, kind=sub_dict.get("type"), params=_sub_params(sub_dict))
            case_factories.append((when, build_generator(sub_spec, rng, context, bounds)))

        default_dict = params.get("default")
        default_factory: Generator | None = None
        if default_dict is not None:
            if not isinstance(default_dict, dict):
                raise FieldTypeError(f"{name}: 'default' must be a field spec object")
            sub_spec = FieldSpec(
                name=name, kind=default_dict.get("type"), params=_sub_params(default_dict)
            )
            default_factory = build_generator(sub_spec, rng, context, bounds)

        def _conditional(row: dict[str, Any]) -> Any:
            current = row.get(condition)
            for when, factory in case_factories:
                if current == when:
                    return factory(row)
            if default_factory is not None:
                return default_factory(row)
            raise FieldTypeError(f"{name}: no case matches '{condition}={current}' and no default")

        return _conditional

    raise FieldTypeError(f"{name}: unsupported field type '{kind}'")


def _sub_params(spec: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in spec.items() if key not in ("name", "type")}


def _range_params(spec: FieldSpec) -> tuple:
    lo = spec.params.get("min")
    hi = spec.params.get("max")
    if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
        raise FieldTypeError(f"{spec.name}: 'min'/'max' numbers required")
    if lo > hi:
        raise FieldTypeError(f"{spec.name}: 'min' must be <= 'max'")
    return lo, hi


def _date_params(spec: FieldSpec, bounds: Any | None, kind: str) -> tuple:
    params = dict(spec.params)
    for key in ("start", "end"):
        if key not in params:
            if bounds is None:
                raise FieldTypeError(f"{spec.name}: '{key}' required or a generation window needed")
            params[key] = getattr(bounds, key).isoformat()
    fmt = params.get("format")
    if fmt is None:
        fmt = "%Y-%m-%d" if kind == "date" else "%Y-%m-%d %H:%M:%S"
    if not isinstance(fmt, str):
        raise FieldTypeError(f"{spec.name}: 'format' must be a string")
    try:
        start_date = date.fromisoformat(params["start"])
        end_date = date.fromisoformat(params["end"])
    except (TypeError, ValueError) as exc:
        raise FieldTypeError(
            f"{spec.name}: invalid {kind} range '{params.get('start')}'..'{params.get('end')}'"
        ) from exc
    if start_date > end_date:
        raise FieldTypeError(f"{spec.name}: start must not be after end")
    if kind == "date":
        return start_date, end_date, fmt
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)
    return start_dt, end_dt, fmt


def _to_seconds(dt: datetime) -> int:
    """Timezone-independent second count for naive datetime arithmetic."""
    return dt.toordinal() * 86400 + dt.hour * 3600 + dt.minute * 60 + dt.second


def _from_seconds(seconds: int) -> datetime:
    return datetime.fromordinal(seconds // 86400) + timedelta(seconds=seconds % 86400)


def _expand_pattern(pattern: str, rng: random.Random) -> str:
    chars = []
    for char in pattern:
        if char == "#":
            chars.append(rng.choice(_DIGITS))
        elif char == "@":
            chars.append(rng.choice(_UPPER))
        else:
            chars.append(char)
    return "".join(chars)
