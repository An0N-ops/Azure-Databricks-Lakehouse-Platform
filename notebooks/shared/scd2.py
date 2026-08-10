"""Pure-Python reference semantics for SCD Type 2 on Silver tables.

This module is the **test oracle** for the platform's SCD2 pattern. At runtime
Lakeflow materializes the same behavior with ``dp.create_auto_cdc_flow`` using
``track_history_column_list`` and ``stored_as_scd_type=2`` (see
:func:`notebooks.shared.silver.register_silver`). The Lakeflow engine is the
only runtime implementation; this module exists so the *semantics* are
reviewable and pinable in pure Python, which is the repository's CI test
strategy for the declarative layers (docs/development.md).

Semantics contract:

* Changes are grouped by business key and applied in sequence order.
* The first change for a key opens a version with ``effective_from`` set,
  ``effective_to`` unset, and ``is_current`` true.
* A change whose *tracked* attributes differ from the current version closes
  it (``effective_to`` = the new change's sequence value, ``is_current``
  false) and opens a fresh version.
* A change whose tracked attributes are identical (a repeat) opens nothing:
  the current version stands, so duplicate deliveries do not grow history.
* Changes to untracked attributes do not open a version; they are absorbed
  into the current version (in-place update semantics).
* Rows with null business keys are ignored, mirroring ``ignore_null_keys``.

Output rows carry the original change fields plus ``effective_from``,
``effective_to`` (``None`` = open/current), and ``is_current``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

EFFECTIVE_FROM = "effective_from"
EFFECTIVE_TO = "effective_to"
IS_CURRENT = "is_current"


def apply_scd2(
    changes: Sequence[Mapping[str, Any]],
    *,
    keys: Sequence[str],
    track_by: Sequence[str],
    sequence_by: str,
) -> list[dict[str, Any]]:
    """Fold an ordered change feed into SCD Type 2 version rows.

    ``changes`` must already be ordered by delivery/sequence (in the pipeline
    that order is ``_ingested_at``). ``keys`` is the business key, ``track_by``
    the attributes whose change opens a new version, and ``sequence_by`` the
    column whose value stamps ``effective_from``/``effective_to``.

    Returns a list of version rows (original fields + the three version
    attributes), grouped per business key and ordered by first appearance.
    Deterministic for the same input.
    """
    versions_by_key: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for change in changes:
        key = tuple(change[column] for column in keys)
        if any(value is None for value in key):
            continue
        versions = versions_by_key.setdefault(key, [])
        current = versions[-1] if versions else None
        if current is None:
            versions.append(_open_version(change, sequence_by, track_by))
            continue
        if _tracked_values(current, track_by) == _tracked_values(change, track_by):
            current.update({k: v for k, v in change.items() if k not in VERSION_ATTRIBUTES})
            continue
        current[EFFECTIVE_TO] = change.get(sequence_by)
        current[IS_CURRENT] = False
        versions.append(_open_version(change, sequence_by, track_by))
    return [version for versions in versions_by_key.values() for version in versions]


VERSION_ATTRIBUTES = frozenset({EFFECTIVE_FROM, EFFECTIVE_TO, IS_CURRENT})


def _open_version(
    change: Mapping[str, Any], sequence_by: str, track_by: Sequence[str]
) -> dict[str, Any]:
    version = {EFFECTIVE_FROM: change.get(sequence_by), EFFECTIVE_TO: None, IS_CURRENT: True}
    version.update(change)
    return version


def _tracked_values(version: Mapping[str, Any], track_by: Sequence[str]) -> tuple[Any, ...]:
    return tuple(version.get(column) for column in track_by)
