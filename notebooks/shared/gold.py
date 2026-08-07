"""Shared PySpark helpers for Gold star-schema models (ADR-005).

Gold tables are registered from a declarative manifest. Dimensions read their
Silver source and enforce fail-on-violation expectations. The date dimension is
generated from a declared date range. Facts read a Silver source, derive an
integer ``date_key`` (``YYYYMMDD``) from a timestamp/date column, and may
aggregate measures at a declared grain (e.g. daily sensor telemetry). PySpark
and DLT imports stay inside functions so the module imports and lints without
a Spark runtime — the Gold test strategy is pure Python against the manifests
(see docs/development.md).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import gold_manifest
from .ingest import apply_expectations

DATE_KEY_ALIAS = "date_key"
CHANGE_DATA_FEED = {"delta.enableChangeDataFeed": "true"}


def date_key_expr(column: str) -> Any:
    """Build the ``YYYYMMDD`` integer surrogate-key expression for a column.

    Matches :func:`notebooks.shared.gold_manifest.date_dimension_rows`, so a
    fact's ``date_key`` joins directly to ``dim_date.date_key``.
    """
    from pyspark.sql import functions as F

    return (
        F.year(F.col(column)) * 10000 + F.month(F.col(column)) * 100 + F.dayofmonth(F.col(column))
    ).cast("int")


def gold_source(
    spark: Any, spec: Mapping[str, Any], *, variables: Mapping[str, str] | None = None
) -> Any:
    """Read the Silver source and apply kind-specific Gold transformations.

    Dimensions read their Silver table unchanged. The date dimension is built
    from :func:`notebooks.shared.gold_manifest.date_dimension_rows`. Facts
    derive ``date_key``; aggregate facts also collapse measures to the declared
    grain (``group_by`` + ``date_key``).

    Returns a batch read; use :func:`gold_stream_source` for an incremental
    streaming read of the source.
    """

    kind = spec["kind"]
    if kind == "date_dimension":
        return spark.createDataFrame(
            gold_manifest.date_dimension_rows(
                spec["date_range"]["start"], spec["date_range"]["end"]
            )
        )

    df = spark.table(gold_manifest.resolve_source_table(spec, variables))

    if kind == "fact" and spec.get("aggregate"):
        aggregate = spec["aggregate"]
        df = df.withColumn(DATE_KEY_ALIAS, date_key_expr(aggregate["date_key"]["column"]))
        group_by = list(aggregate["group_by"]) + [DATE_KEY_ALIAS]
        return df.groupBy(*group_by).agg(
            *[_aggregation_expr(measure) for measure in aggregate["measures"]]
        )

    if kind == "fact":
        date_key = spec.get("date_key")
        if date_key is not None:
            df = df.withColumn(DATE_KEY_ALIAS, date_key_expr(date_key["column"]))

    return df


def gold_stream_source(
    spark: Any, spec: Mapping[str, Any], *, variables: Mapping[str, str] | None = None
) -> Any:
    """Read the Silver source as a streaming read for incremental Gold.

    Silver now enables the Change Data Feed, so a streaming read here lets Gold
    continue to update incrementally as Silver upserts rows, instead of a
    full batch scan every run. The date dimension and aggregate facts are not
    built from this path (see :func:`gold_source`).
    """
    df = spark.readStream.table(gold_manifest.resolve_source_table(spec, variables))
    if spec["kind"] == "fact":
        date_key = spec.get("date_key")
        if date_key is not None:
            df = df.withColumn(DATE_KEY_ALIAS, date_key_expr(date_key["column"]))
    return df


def _aggregation_expr(measure: Mapping[str, str]) -> Any:
    from pyspark.sql import functions as F

    column = F.col(measure["column"])
    aggregation = measure["agg"]
    if aggregation == "sum":
        expression = F.sum(column)
    elif aggregation == "avg":
        expression = F.avg(column)
    elif aggregation == "min":
        expression = F.min(column)
    elif aggregation == "max":
        expression = F.max(column)
    elif aggregation == "count":
        expression = F.count(column)
    elif aggregation == "count_true":
        expression = F.sum(F.when(column, F.lit(1)).otherwise(F.lit(0)))
    else:  # pragma: no cover - guarded by manifest validation
        raise ValueError(f"unsupported aggregation '{aggregation}' for measure '{measure['as']}'")
    return expression.alias(measure["as"])


def _gold_keys(spec: Mapping[str, Any]) -> list[str]:
    """Normalize a Gold primary key to a list of CDC key columns."""
    primary_key = spec["primary_key"]
    return list(primary_key) if isinstance(primary_key, list) else [primary_key]


def register_gold(
    spec: Mapping[str, Any],
    *,
    target_schema: str = "gold",
    variables: Mapping[str, str] | None = None,
) -> Any:
    """Register a Gold table with fail-on-violation DLT expectations.

    The target is the schema-qualified ``"{target_schema}.{name}"`` so a single
    DLT pipeline can own tables across the bronze/silver/gold schemas. The table
    comment is the spec's description. Expectations use the Silver-to-Gold
    **fail** policy (ADR-005): an update that violates a Gold quality contract
    aborts the pipeline rather than silently producing a bad analytics table.

    Dimensions and non-aggregate facts are registered as **streaming
    Change Data Capture upserts**: a prep table reads the Silver Change Data
    Feed and ``apply_changes`` mirrors Silver's updates/deletes into Gold
    incrementally. The date dimension and aggregate facts stay materialized
    views (a batch read over Silver), which is the standard for gold-layer
    aggregations.
    """
    import dlt

    target_name = f"{target_schema}.{spec['name']}"
    kind = spec["kind"]

    if kind == "date_dimension" or (kind == "fact" and spec.get("aggregate")):
        # Materialized view path (also used for the generated date dimension)
        def _source() -> Any:
            from pyspark.sql import SparkSession

            return gold_source(
                SparkSession.getActiveSession(),
                spec,
                variables=variables,
            )

        _source.__name__ = target_name
        _source.__doc__ = spec.get("description")
        return apply_expectations(
            dlt.table(
                name=target_name,
                comment=spec.get("description", ""),
                table_properties=CHANGE_DATA_FEED,
            )(_source),
            spec,
            on_violation="fail",
        )

    # Streaming CDC path: prep streams Silver's changes, target upserts SCD-1
    prep_name = f"{target_schema}.gold_source_{spec['name']}"

    def _prep() -> Any:
        from pyspark.sql import SparkSession

        return gold_stream_source(
            SparkSession.getActiveSession(),
            spec,
            variables=variables,
        )

    _prep.__name__ = prep_name
    _prep.__doc__ = f"Streaming Silver source for gold.{spec['name']}"
    apply_expectations(
        dlt.table(
            name=prep_name,
            comment=f"Streaming Silver source for gold.{spec['name']}",
            table_properties=CHANGE_DATA_FEED,
        )(_prep),
        spec,
        on_violation="fail",
    )
    dlt.create_streaming_table(
        name=target_name,
        comment=spec.get("description", ""),
        table_properties=CHANGE_DATA_FEED,
    )
    dlt.apply_changes(
        target=target_name,
        source=prep_name,
        keys=_gold_keys(spec),
        sequence_by="_updated_at",
    )
