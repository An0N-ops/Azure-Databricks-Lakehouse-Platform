"""Bronze DLT pipeline for the Energy industry pack.

Declaratively registers one Auto Loader streaming table per entity defined in
``pipelines/energy/bronze_manifest.json`` (ADR-004, ADR-005). Manifest
placeholders are resolved from environment variables (see
``notebooks/shared/bronze_manifest.py``) so this notebook runs unchanged in
dev, qa, and prod.
"""

import sys
from pathlib import Path


def _repo_root(start: Path) -> Path:
    """Climb to the repository root (marked by pyproject.toml) so ``notebooks.shared`` imports."""
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").is_file() or (parent / ".git").is_dir():
            return parent
    return start


_start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
ROOT = _repo_root(_start)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notebooks.shared import bronze_manifest, ingest

MANIFEST = bronze_manifest.load_manifest(ROOT / "pipelines" / "energy" / "bronze_manifest.json")
SPECS = bronze_manifest.table_specs(MANIFEST)

for spec in SPECS:
    ingest.dlt_bronze_table(spec)
