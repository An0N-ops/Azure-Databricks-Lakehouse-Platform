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
        .withColumn("_source_file", F.input_file_name())
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
    ``"drop"`` (default) drops violating rows, while ``"retain"`` keeps them
    and records the violation in the DLT event log — the policy used at the
    Bronze-to-Silver boundary so raw provenance is preserved.
    """
    import dlt

    if on_violation not in ("drop", "retain"):
        raise ValueError(f"unsupported on_violation policy: {on_violation}")

    decorator = dlt.expect if on_violation == "drop" else dlt.expect_or_retain
    for expectation in spec.get("expectations", []):
        func = decorator(expectation["name"], expectation["constraint"])(func)
    return func


def dlt_bronze_table(
    spec: Mapping[str, Any],
    *,
    variables: Mapping[str, str] | None = None,
    commit_id: str | None = None,
) -> Any:
    """Register a DLT Bronze table for a manifest table spec.

    The returned function is the decorator-applied streaming definition; DLT
    derives the target table name from ``spec["name"]``.
    """
    import dlt

    def _ingest() -> Any:
        return bronze_stream(
            spark,  # noqa: F821 - provided by the Databricks notebook runtime
            spec,
            variables=variables,
            commit_id=commit_id,
        )

    _ingest.__name__ = spec["name"]
    _ingest.__doc__ = spec.get("description")
    return apply_expectations(
        dlt.table(name=spec["name"], comment=spec.get("description", ""))(_ingest),
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
