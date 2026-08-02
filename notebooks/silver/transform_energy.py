"""Silver DLT pipeline for the Energy industry pack.

Declaratively registers one conformed Silver table per entity defined in
``pipelines/energy/silver_manifest.json`` (ADR-004, ADR-005). Each table reads
its Bronze counterpart, normalizes fields, drops rows that violate quality
expectations, and upserts by natural key (SCD Type 1) via
``dlt.apply_changes``. Placeholders resolve from environment variables so this
notebook runs unchanged in dev, qa, and prod.
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

from notebooks.shared import silver, silver_manifest

MANIFEST = silver_manifest.load_silver_manifest(
    ROOT / "pipelines" / "energy" / "silver_manifest.json"
)
silver_manifest.validate_silver_manifest(MANIFEST)

for spec in silver_manifest.table_specs(MANIFEST):
    silver.register_silver(spec)
