"""Shared PySpark helpers for Silver conformed transformations (ADR-005).

Silver tables read their Bronze counterpart, apply declarative per-column
conforming rules, add the ``_updated_at`` audit column, and upsert by natural
key via ``dlt.apply_changes``. Tables default to SCD Type 1; a manifest spec
can opt into SCD Type 2 with ``"scd_type": 2`` plus a ``track_by`` column list
(spec declares which attributes drive a new historical version). The SCD2
behavior is pinned by the pure-Python oracle in :mod:`notebooks.shared.scd2`
(see tests/test_scd2.py). PySpark/DLT imports stay inside functions so the
module imports and lints without a Spark runtime; the Silver test strategy is
pure Python against the manifests (see docs/development.md).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import silver_manifest
from .ingest import apply_expectations


def apply_conform(df: Any, conform: Mapping[str, list[Mapping[str, Any]]] | None) -> Any:
    """Apply per-column conforming rules in declaration order.

    Rules are the vocabulary declared by
    :data:`notebooks.shared.silver_manifest.SUPPORTED_CONFORM_RULES`:
    ``trim``, ``lower``, ``upper``, ``initcap``, ``coalesce`` (requires
    ``value``), and ``cast`` (requires ``type``).
    """
    from pyspark.sql import functions as F

    result = df
    for column, rules in (conform or {}).items():
        column_expr = F.col(column)
        for rule in rules:
            name = rule["rule"]
            if name == "trim":
                column_expr = F.trim(column_expr)
            elif name == "lower":
                column_expr = F.lower(column_expr)
            elif name == "upper":
                column_expr = F.upper(column_expr)
            elif name == "initcap":
                column_expr = F.initcap(column_expr)
            elif name == "coalesce":
                column_expr = F.coalesce(column_expr, F.lit(rule["value"]))
            elif name == "cast":
                column_expr = column_expr.cast(rule["type"])
            else:  # pragma: no cover - guarded by manifest validation
                raise ValueError(f"unsupported conform rule '{name}' for column '{column}'")
        result = result.withColumn(column, column_expr)
    return result


def with_updated_at(df: Any) -> Any:
    """Attach the ``_updated_at`` audit column required on Silver tables."""
    from pyspark.sql import functions as F

    return df.withColumn("_updated_at", F.current_timestamp())


def conformed_bronze(
    spark: Any,
    spec: Mapping[str, Any],
    *,
    variables: Mapping[str, str] | None = None,
) -> Any:
    """Read a spec's Bronze table as a streaming source and apply conforming.

    Uses ``spark.readStream.table`` so the prep table consumes the Bronze
    Change Data Feed (Bronze now enables ``delta.enableChangeDataFeed``). This
    keeps Silver incremental and database-fied even when Bronze receives
    non-append commits (updates/deletes/overwrites), the canonical
    ``DELTA_SOURCE_TABLE_IGNORE_CHANGES`` mitigation.
    """
    source_table = silver_manifest.resolve_source_table(spec, variables)
    df = spark.readStream.table(source_table)
    return with_updated_at(apply_conform(df, spec.get("conform")))


def register_silver(
    spec: Mapping[str, Any],
    *,
    target_schema: str = "silver",
    variables: Mapping[str, str] | None = None,
) -> Any:
    """Register a Silver table: conformed source prep table + SCD upsert.

    The prep table carries the spec's DLT expectations under the Bronze-to-
    Silver retain policy (ADR-005): violating rows are kept and flagged in the
    DLT event log rather than dropped. Rows with null keys are skipped by the
    upsert (``ignore_null_keys``) so they never corrupt the SCD target, while
    still being visible in Bronze.

    The prep reads Bronze from its Change Data Feed (streaming), so Silver
    tracks every insert/update/delete in Bronze. The SCD target enables the
    Change Data Feed as well, so Gold can ingest Silver's own change commits
    incrementally instead of snapshotting the table.

    Slowly changing dimensions: tables are SCD Type 1 by default. When the
    spec declares ``scd_type: 2`` it must also declare ``track_by``, the list
    of conformed attributes whose change opens a new historical version (the
    DLT ``stored_as_scd_type=2`` + ``track_by`` pattern). Repeated records
    with identical tracked attributes update nothing; untracked attributes
    update the current version in place. The semantics contract is pinned by
    :func:`notebooks.shared.scd2.apply_scd2`.

    Targets are schema-qualified (``{target_schema}.{name}``) so a single DLT
    pipeline can span the bronze/silver/gold schemas.
    """
    import dlt

    target_name = f"{target_schema}.{spec['name']}"
    prep_name = f"{target_schema}.silver_source_{spec['name']}"

    def _prep() -> Any:
        from pyspark.sql import SparkSession

        return conformed_bronze(
            SparkSession.getActiveSession(),
            spec,
            variables=variables,
        )

    _prep.__name__ = prep_name
    _prep.__doc__ = f"Conformed Bronze source for silver.{spec['name']}"
    apply_expectations(
        dlt.table(
            name=prep_name,
            comment=f"Conformed Bronze source for silver.{spec['name']}",
            table_properties={"delta.enableChangeDataFeed": "true"},
        )(_prep),
        spec,
        on_violation="retain",
    )
    dlt.create_streaming_table(
        name=target_name,
        comment=f"Silver {spec['name']} target (CDC)",
        table_properties={"delta.enableChangeDataFeed": "true"},
    )
    scd_type = int(spec.get("scd_type", 1))
    if scd_type == 2:
        dlt.apply_changes(
            target=target_name,
            source=prep_name,
            keys=list(spec["keys"]),
            sequence_by="_ingested_at",
            ignore_null_keys=True,
            track_by=list(spec["track_by"]),
            stored_as_scd_type=2,
        )
    else:
        dlt.apply_changes(
            target=target_name,
            source=prep_name,
            keys=list(spec["keys"]),
            sequence_by="_ingested_at",
            ignore_null_keys=True,
            stored_as_scd_type=1,
        )
