import copy
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA_DIR = REPO_ROOT / "sample-data"
if str(SAMPLE_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(SAMPLE_DATA_DIR))


@pytest.fixture(scope="session")
def config_path():
    return SAMPLE_DATA_DIR / "sample_data" / "industries" / "energy" / "config.json"


@pytest.fixture(scope="session")
def industry_config(config_path):
    from sample_data.config import load_config

    return load_config(config_path)


@pytest.fixture(scope="session")
def small_config(industry_config):
    """The real energy pack with small volumes so tests run fast."""
    config = copy.deepcopy(industry_config)
    volumes = {
        "customers": 12,
        "locations": 8,
        "assets": 20,
        "employees": 15,
        "inventory": 25,
        "work_orders": 40,
        "maintenance_events": {"rows_per_reference": "assets", "rows_per_unit": 2},
        "weather": {"rows_per_reference": "locations", "rows_per_unit": 5},
        "iot_events": {"rows_per_reference": "assets", "rows_per_unit": 4},
    }
    for name, volume in volumes.items():
        config["entities"][name]["volume"] = volume
    return config


@pytest.fixture(scope="session")
def small_data(small_config):
    from sample_data.engine import generate

    return generate(small_config, seed=42)
