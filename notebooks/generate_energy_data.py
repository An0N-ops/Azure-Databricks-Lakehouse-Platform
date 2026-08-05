# Databricks notebook source
# MAGIC %python
"""
Synthetic data generation for the Lakehouse medallion pipelines.

Runs inside Databricks as a bundle job. It exercises the repository's
``sample-data/sample_data`` package (synced into the bundle) to produce a
deterministic batch of landing files, writing them directly into the Bronze
Unity Catalog volume that the Bronze Auto Loader pipeline watches.

The generator writes date-partitioned folders:
    {landing}/energy/<entity>/batch_date=YYYY-MM-DD/<entity>.csv
which the DLT Bronze pipeline consumes from ``{landing}/energy/*``.

Used by bundle job ``resources.jobs.generate_energy_data``.
"""

import sys
from datetime import date
from pathlib import Path

# Locate the synced bundle files so the sample-data package can be imported.
# Workspace files are mounted at /Workspace/... on the driver's local FS, but
# notebookPath() may be returned without the /Workspace prefix, so normalize it.
_nb = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
if not _nb.startswith("/Workspace"):
    _nb = "/Workspace" + _nb
_files_root = _nb.rsplit("/notebooks/", 1)[0]
_sample_dir = Path(_files_root) / "sample-data"
_config_dir = _sample_dir / "sample_data" / "industries"

if not _config_dir.is_dir():
    _tmp = Path("/local_disk0/sample-data")
    if _tmp.exists():
        import shutil

        shutil.rmtree(_tmp)
    dbutils.fs.cp(str(_sample_dir), "file:/local_disk0/sample-data", recurse=True)
    _sample_dir = _tmp
    _config_dir = _sample_dir / "sample_data" / "industries"

if str(_sample_dir) not in sys.path:
    sys.path.insert(0, str(_sample_dir))

# --- Databricks runtime imports (available inside a job) ----------------------
from sample_data.config import load_config
from sample_data.engine import generate
from sample_data.writers import write_batch

_catalog = dbutils.widgets.get("catalog")
_landing = dbutils.widgets.get("landing_path")

_config = load_config(_config_dir / "energy" / "config.json")

_seed = 42
_scale = 1.0
_data = generate(_config, seed=_seed, scale=_scale)
_as_of = date.today()
_start = date.fromisoformat(_config["metadata"]["default_start_date"])
_end = date.fromisoformat(_config["metadata"]["default_end_date"])

_files, _manifest = write_batch(
    output_root=_landing,
    industry="energy",
    data=_data,
    seed=_seed,
    as_of_date=_as_of,
    start_date=_start,
    end_date=_end,
    scale=_scale,
    metadata=_config["metadata"],
    fmt="csv",
)

for path in _files[:3]:
    print("wrote", path)
print("entity counts:", _manifest["entity_counts"])
print("done")