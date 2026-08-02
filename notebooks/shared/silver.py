"""Shared PySpark helpers for Silver conformed transformations (ADR-005).

Silver tables read their Bronze counterpart, apply declarative per-column
conforming rules, add the ``_updated_at`` audit column, and upsert by natural
key (SCD Type 1) via ``dlt.apply_changes``. PySpark/DLT imports stay inside
functions so the module imports and lints without a Spark runtime; the Silver
test strategy is pure Python against the manifests (see docs/development.md).
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
    """Read a spec's Bronze table and apply conforming plus ``_updated_at``."""
    source_table = silver_manifest.resolve_source_table(spec, variables)
    df = spark.table(source_table)
    return with_updated_at(apply_conform(df, spec.get("conform")))


def register_silver(
    spec: Mapping[str, Any],
    *,
    variables: Mapping[str, str] | None = None,
) -> Any:
    """Register a Silver table: conformed source prep table + SCD Type 1 upsert.

    The prep table carries the spec's DLT expectations under the Bronze-to-
    Silver retain policy (ADR-005): violating rows are kept and flagged in the
    DLT event log rather than dropped. Rows with null keys are skipped by the
    upsert (``ignore_null_keys``) so they never corrupt the SCD target, while
    still being visible in Bronze.
    """
    import dlt

    name = spec["name"]
    prep_name = f"silver_source_{name}"

    def _prep() -> Any:
        return conformed_bronze(
            spark,  # noqa: F821 - provided by the Databricks notebook runtime
            spec,
            variables=variables,
        )

    _prep.__name__ = prep_name
    _prep.__doc__ = f"Conformed Bronze source for silver.{name}"
    apply_expectations(
        dlt.table(name=prep_name, comment=f"Conformed Bronze source for silver.{name}")(_prep),
        spec,
        on_violation="retain",
    )
    dlt.apply_changes(
        target=name,
        source=prep_name,
        keys=list(spec["keys"]),
        sequence_by="_ingested_at",
        ignore_null_keys=True,
        ignore_null_updates=False,
        apply_as_append=False,
    )
