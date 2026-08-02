"""Writers that persist generated rows to disk for downstream ingestion.

Output is date-partitioned by ``batch_date`` (``batch_date=YYYY-MM-DD``) so an
incremental loader such as Databricks Auto Loader can consume new batches
without reprocessing history. A ``manifest.json`` captures the provenance of
every run (seed, window, entity counts) for reproducibility.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sample_data import __version__


def write_batch(
    output_root: Path,
    industry: str,
    data: dict[str, list[dict[str, Any]]],
    *,
    seed: int,
    as_of_date,
    start_date,
    end_date,
    scale: float,
    metadata: dict[str, Any],
    fmt: str = "csv",
    parquet: bool = False,
) -> tuple[list[Path], dict[str, Any]]:
    """Write every entity plus a manifest, returning ``(files, manifest)``."""
    if fmt not in ("csv", "json"):
        raise ValueError(f"unsupported output format: {fmt}")

    files: list[Path] = []
    for entity, rows in data.items():
        entity_dir = _entity_dir(output_root, industry, entity, as_of_date)
        entity_dir.mkdir(parents=True, exist_ok=True)
        base = entity_dir / entity
        if fmt == "csv":
            files.append(write_entity_csv(base.with_suffix(".csv"), rows))
        else:
            files.append(write_entity_json(base.with_suffix(".json"), rows))
        if parquet:
            files.append(write_entity_parquet(base.with_suffix(".parquet"), rows))

    manifest = build_manifest(
        industry=industry,
        data=data,
        seed=seed,
        as_of_date=as_of_date,
        start_date=start_date,
        end_date=end_date,
        scale=scale,
        metadata=metadata,
    )
    manifest_path = Path(output_root) / industry / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    files.append(manifest_path)
    return files, manifest


def write_entity_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
    if not rows:
        path.write_text("", encoding="utf-8")
        return path
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_entity_json(path: Path, rows: list[dict[str, Any]]) -> Path:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)
    return path


def write_entity_parquet(path: Path, rows: list[dict[str, Any]]) -> Path:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - exercised only without pyarrow
        raise RuntimeError("parquet output requires pyarrow to be installed") from exc
    if not rows:
        table = pa.table({"__empty__": pa.array([], type=pa.string())})
    else:
        columns = list(rows[0].keys())
        arrays = []
        for column in columns:
            values = [row.get(column) for row in rows]
            arrays.append(pa.array(values))
        table = pa.Table.from_arrays(arrays, names=columns)
    pq.write_table(table, path)
    return path


def build_manifest(
    *,
    industry: str,
    data: dict[str, list[dict[str, Any]]],
    seed: int,
    as_of_date,
    start_date,
    end_date,
    scale: float,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "generator_version": __version__,
        "industry": industry,
        "company": metadata.get("company"),
        "seed": seed,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "as_of_date": as_of_date.isoformat(),
        "scale": scale,
        "entity_counts": {entity: len(rows) for entity, rows in data.items()},
        "generated_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
    }


def _entity_dir(output_root: Path, industry: str, entity: str, as_of_date) -> Path:
    return Path(output_root) / industry / entity / f"batch_date={as_of_date.isoformat()}"
