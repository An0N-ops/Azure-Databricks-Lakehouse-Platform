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


def _sync_root() -> Path:
    """Return the bundle sync root (dir containing ``notebooks/`` and ``pipelines/``).

    Inside DLT, ``__file__`` and ``cwd`` are not the notebook's workspace path,
    so prefer the current notebook path from ``dbutils``. Falls back to
    climbing from the script/cwd for local runs.
    """
    candidates: list[Path] = []
    try:
        path = (
            dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
        )
        if path:
            candidates.append(Path(path).parent)
    except Exception:
        pass
    _start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    candidates.append(_start)
    for parent in [*candidates, *(candidates[0].parents if candidates else [])]:
        for root in [parent, *parent.parents]:
            if (root / "notebooks").is_dir() and (root / "pipelines").is_dir():
                return root
    return _start


ROOT = _sync_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notebooks.shared import gold, gold_manifest

MANIFEST = gold_manifest.load_gold_manifest(ROOT / "pipelines" / "energy" / "gold_manifest.json")
gold_manifest.validate_gold_manifest(MANIFEST)

for spec in gold_manifest.table_specs(MANIFEST):
    gold.register_gold(spec, target_schema=MANIFEST.get("schema", "gold"))
