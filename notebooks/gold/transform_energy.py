"""Gold DLT pipeline for the Energy industry pack.

Declaratively registers one Kimball star-schema table per model defined in
``pipelines/energy/gold_manifest.json`` (ADR-004, ADR-005). Dimensions conform
Silver entities, the date dimension is generated from a date range, and facts
derive ``date_key`` and (for telemetry) aggregate measures at a declared grain.
Placeholders resolve from environment variables so this notebook runs unchanged
in dev, qa, and prod.
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

from notebooks.shared import gold, gold_manifest

MANIFEST = gold_manifest.load_gold_manifest(ROOT / "pipelines" / "energy" / "gold_manifest.json")
gold_manifest.validate_gold_manifest(MANIFEST)

for spec in gold_manifest.table_specs(MANIFEST):
    gold.register_gold(spec)
