"""Shared PySpark helpers for Gold star-schema models (ADR-005).

Gold tables are registered from a declarative manifest. Dimensions and
non-aggregate facts are **streaming tables**: a ``@dp.temporary_view`` reads
the Silver source's Change Data Feed, ``dp.create_streaming_table`` creates the
empty target, and ``dp.create_auto_cdc_flow`` (SCD Type 1) upserts changes and
propagates deletes. Silver is written by ``create_auto_cdc_flow`` (MERGE
commits), so a plain streaming read would abort with
``DELTA_SOURCE_TABLE_IGNORE_CHANGES``; reading the change feed is the supported
way to propagate Silver commits into Gold incrementally.

The date dimension is generated from a declared date range and the aggregate
fact (``fact_sensor_daily``) collapses measures at a declared grain — both are
``@dp.materialized_view`` over a batch read, the Lakeflow pattern for
aggregation over a change-fed source (a running streaming aggregation cannot
correctly retract measures after upstream updates, so the materialized view
recomputes from source state). PySpark and Lakeflow imports stay inside
functions so the module imports and lints without a Spark runtime — the Gold
test strategy is pure Python against the manifests (see docs/development.md).
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

    Returns a batch read; used by the materialized views (date dimension and
    aggregate facts), which recompute from source state on refresh.
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
    """Stream a spec's Silver source Change Data Feed into Gold.

    Silver targets are AUTO CDC (MERGE) tables, which plain streaming reads
    reject with ``DELTA_SOURCE_TABLE_IGNORE_CHANGES``; reading with
    ``readChangeFeed = true`` yields one row per changed row with the CDF
    metadata columns (``_change_type``, ``_commit_version``,
    ``_commit_timestamp``). This view pre-cleans the feed before the AUTO CDC
    flow interprets it:

    * ``update_preimage`` rows are dropped — only the post-image matters.
    * For SCD Type 2 Silver sources, the "expired version" post-image
      (``update_postimage`` with ``__END_AT`` set) is dropped as well, so the
      last applied row per business key is always the newest version's insert;
      otherwise the AUTO CDC SCD1 upsert would be ambiguous between the expire
      and the new-version insert of the same commit.
    * The reserved SCD2 columns ``__START_AT`` / ``__END_AT`` are dropped (they
      are physical columns of Silver SCD2 tables); AUTO CDC rejects
      system-reserved column names in the flow source, so they must be removed
      once the expiry filter has consumed ``__END_AT``.

    CDF metadata columns are kept and excluded via ``except_column_list`` on
    the flow; delete rows are applied via ``apply_as_deletes``. ``sequence_by``
    uses ``_commit_timestamp`` so Gold applies changes in commit order.
    """
    from pyspark.sql import functions as F

    df = (
        spark.readStream.format("delta")
        .option("readChangeFeed", "true")
        .table(gold_manifest.resolve_source_table(spec, variables))
        .filter(F.col("_change_type") != "update_preimage")
    )
    if "__END_AT" in df.columns:
        df = df.filter(
            ~((F.col("_change_type") == "update_postimage") & F.col("__END_AT").isNotNull())
        ).drop("__END_AT", "__START_AT")

    kind = spec["kind"]
    if kind == "fact":
        date_key = spec.get("date_key")
        if date_key is not None:
            df = df.withColumn(DATE_KEY_ALIAS, date_key_expr(date_key["column"]))

    return df


def _gold_keys(spec: Mapping[str, Any]) -> list[str]:
    """Return the AUTO CDC key columns for a spec's primary key."""
    primary_key = spec["primary_key"]
    return list(primary_key) if isinstance(primary_key, list) else [primary_key]


def _register_streaming(
    spec: Mapping[str, Any],
    *,
    target_name: str,
    variables: Mapping[str, str] | None,
) -> Any:
    """Register a Gold dimension / fact table as a streaming AUTO CDC table."""
    from pyspark import pipelines as dp
    from pyspark.sql import functions as F

    prep_name = f"gold_source_{spec['name']}"

    def _prep() -> Any:
        from pyspark.sql import SparkSession

        return gold_stream_source(
            SparkSession.getActiveSession(),
            spec,
            variables=variables,
        )

    apply_expectations(
        dp.temporary_view(
            name=prep_name,
            comment=f"Silver source change feed for gold.{spec['name']}",
        )(_prep),
        spec,
        on_violation="fail",
    )
    dp.create_streaming_table(
        name=target_name,
        comment=spec.get("description", ""),
        table_properties=CHANGE_DATA_FEED,
    )
    dp.create_auto_cdc_flow(
        target=target_name,
        source=prep_name,
        keys=_gold_keys(spec),
        sequence_by="_commit_timestamp",
        stored_as_scd_type="1",
        apply_as_deletes=F.expr("_change_type = 'delete'"),
        except_column_list=["_change_type", "_commit_version", "_commit_timestamp"],
    )


def _register_materialized(
    spec: Mapping[str, Any],
    *,
    target_name: str,
    variables: Mapping[str, str] | None,
) -> Any:
    """Register a Gold table as a materialized view over a batch read."""
    from pyspark import pipelines as dp

    def _source() -> Any:
        from pyspark.sql import SparkSession

        return gold_source(
            SparkSession.getActiveSession(),
            spec,
            variables=variables,
        )

    return apply_expectations(
        dp.materialized_view(
            name=target_name,
            comment=spec.get("description", ""),
            table_properties=CHANGE_DATA_FEED,
        )(_source),
        spec,
        on_violation="fail",
    )


def register_gold(
    spec: Mapping[str, Any],
    *,
    target_schema: str = "gold",
    variables: Mapping[str, str] | None = None,
) -> Any:
    """Register a Gold table with fail-on-violation expectations.

    The target is the schema-qualified ``"{target_schema}.{name}"`` so a single
    pipeline can own tables across the bronze/silver/gold schemas. The table
    comment is the spec's description. Expectations use the Silver-to-Gold
    **fail** policy (ADR-005): a change that violates a Gold quality contract
    aborts the pipeline rather than silently producing a bad analytics table.

    Dimensions and non-aggregate facts register as **streaming tables**
    (temporary view over the Silver change feed + AUTO CDC flow, see
    :func:`gold_stream_source`). The generated date dimension and the aggregate
    fact register as **materialized views** (:func:`gold_source`): the
    aggregation needs the source's complete state to compute correct sums (a
    streaming aggregation cannot retract superseded readings), and the date
    dimension has no Silver source at all.
    """
    target_name = f"{target_schema}.{spec['name']}"

    if spec["kind"] == "date_dimension" or (spec["kind"] == "fact" and spec.get("aggregate")):
        return _register_materialized(
            spec,
            target_name=target_name,
            variables=variables,
        )
    return _register_streaming(
        spec,
        target_name=target_name,
        variables=variables,
    )


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
