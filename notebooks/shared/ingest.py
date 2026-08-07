"""Shared PySpark helpers for Bronze Auto Loader ingestion.

These helpers are consumed by DLT notebooks under ``notebooks/bronze/``. They
keep PySpark and DLT imports inside functions so the module can be imported and
linted without a Spark runtime — the Bronze test strategy is pure Python and
exercises :mod:`notebooks.shared.bronze_manifest` only (see docs/development.md).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import bronze_manifest

AUDIT_COLUMNS = ("_ingested_at", "_source_file", "_commit_id")


def with_audit_columns(df: Any, *, commit_id: str | None = None) -> Any:
    """Attach the medallion audit metadata columns to a Bronze DataFrame.

    Adds ``_ingested_at`` (current timestamp), ``_source_file`` (input file
    name), and ``_commit_id`` (batch/run identifier) per the audit contract in
    docs/architecture.md. When ``commit_id`` is omitted it is derived from the
    active Databricks pipeline/job id, falling back to the Spark application id.
    """
    from pyspark.sql import functions as F

    return (
        df.withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.col("_metadata.file_path"))
        .withColumn("_commit_id", F.lit(commit_id or _default_commit_id(df)))
    )


def autoloader_reader(
    spark: Any,
    *,
    source_path: str,
    fmt: str,
    options: Mapping[str, str] | None = None,
) -> Any:
    """Build an Auto Loader (``cloudFiles``) streaming reader for a source.

    ``source_path`` is the absolute landing location produced by
    :func:`notebooks.shared.bronze_manifest.resolve_source_path`. Auto Loader
    discovers files in subdirectories (e.g. the generator's
    ``batch_date=YYYY-MM-DD`` partitions) incrementally and tracks processed
    files in a checkpoint, so re-running a pipeline is idempotent.
    """
    reader = spark.readStream.format("cloudFiles").option("cloudFiles.format", fmt)
    for key, value in (options or {}).items():
        reader = reader.option(key, value)
    return reader.load(source_path)


def bronze_stream(
    spark: Any,
    spec: Mapping[str, Any],
    *,
    variables: Mapping[str, str] | None = None,
    commit_id: str | None = None,
) -> Any:
    """Return a streaming Bronze DataFrame for a manifest table spec.

    ``variables`` override the environment-driven placeholders (see
    :func:`notebooks.shared.bronze_manifest.resolve_source_path`).
    """
    source_path = bronze_manifest.resolve_source_path(spec, variables)
    source = spec["source"]
    return with_audit_columns(
        autoloader_reader(
            spark,
            source_path=source_path,
            fmt=source["format"],
            options=source.get("options"),
        ),
        commit_id=commit_id,
    )


def apply_expectations(func: Any, spec: Mapping[str, Any], *, on_violation: str = "drop") -> Any:
    """Apply a spec's DLT quality expectations to a table function.

    Each expectation in ``spec["expectations"]`` is applied in declaration
    order so violations are reported with the manifest-provided name.

    ``on_violation`` selects the DLT boundary policy (ADR-005):
    ``"drop"`` (default) drops violating rows, ``"retain"`` keeps them and
    records the violation in the DLT event log (the Bronze-to-Silver policy),
    and ``"fail"`` aborts the update (the Gold policy).
    """
    import dlt

    if on_violation not in ("drop", "retain", "fail"):
        raise ValueError(f"unsupported on_violation policy: {on_violation}")

    if on_violation == "drop":
        decorator = dlt.expect_or_drop
    elif on_violation == "retain":
        decorator = dlt.expect
    else:
        decorator = dlt.expect_or_fail
    for expectation in spec.get("expectations", []):
        func = decorator(expectation["name"], expectation["constraint"])(func)
    return func


CDF_PROPERTY = "delta.enableChangeDataFeed"


def dlt_bronze_table(
    spec: Mapping[str, Any],
    *,
    target_schema: str = "bronze",
    variables: Mapping[str, str] | None = None,
    commit_id: str | None = None,
) -> Any:
    """Register a DLT Bronze table for a manifest table spec.

    The target is the schema-qualified ``"{target_schema}.{name}"`` so a single
    DLT pipeline can own tables across schemas (bronze/silver/gold). DLT derives
    the fully-qualified name as ``{catalog}.{schema}.{table}``.

    Change Data Feed is enabled on every Bronze table (``delta.enableChangeDataFeed =
    true``) so downstream Silver/Gold flows can consume inserts, updates, and
    deletes instead of failing on non-append source commits (the standard
    ``DELTA_SOURCE_TABLE_IGNORE_CHANGES`` mitigation).
    """
    import dlt

    target_name = f"{target_schema}.{spec['name']}"

    def _ingest() -> Any:
        from pyspark.sql import SparkSession

        return bronze_stream(
            SparkSession.getActiveSession(),
            spec,
            variables=variables,
            commit_id=commit_id,
        )

    _ingest.__name__ = target_name
    _ingest.__doc__ = spec.get("description")
    return apply_expectations(
        dlt.table(
            name=target_name,
            comment=spec.get("description", ""),
            table_properties={CDF_PROPERTY: "true"},
        )(_ingest),
        spec,
        on_violation="retain",
    )


def _default_commit_id(df: Any) -> str:
    spark = df.sparkSession
    return (
        spark.conf.get("spark.databricks.pipelineJobId", None)
        or spark.conf.get("spark.databricks.job.id", None)
        or spark.sparkContext.applicationId
    )
