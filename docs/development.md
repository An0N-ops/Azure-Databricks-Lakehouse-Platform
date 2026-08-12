# Developer Guide & Local Standards

## Developer Environment Setup

This document outlines the local setup, coding standards, testing workflows, and best practices for engineers contributing to the **Azure Databricks Lakehouse Platform**.

---

## 1. Local Python Environment Configuration

We recommend using Python 3.11 with a virtual environment managed by `venv` or `conda`:

```bash
# Create virtual environment
python -m venv .venv

# Activate environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate environment (Linux/macOS)
source .venv/bin/activate

# Upgrade pip and install development dependencies
pip install --upgrade pip
pip install ruff pytest chispa databricks-connect pyyaml
```

---

## 2. Databricks Connect v2 Integration

Databricks Connect v2 allows developers to write, run, and debug PySpark code locally while executing Spark computations against a Databricks compute cluster in Azure.

### Setup Steps
1. Ensure your Databricks cluster is running Databricks Runtime (DBR) 14.3 LTS or higher.
2. Obtain a Personal Access Token (PAT) or use Azure CLI authentication.
3. Configure your local connection environment variables:

   ```bash
   export DATABRICKS_HOST="https://adb-XXXXXXXXXXXXXXXX.XX.azuredatabricks.net"
   export DATABRICKS_TOKEN="dapixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   export DATABRICKS_CLUSTER_ID="0000-000000-xxxx000"
   ```

4. Test connection in Python:

   ```python
   from databricks.connect import DatabricksSession

   spark = DatabricksSession.builder.getOrCreate()

   df = spark.sql("SELECT current_date(), current_user()")
   df.show()
   ```

---

## 3. PySpark & SQL Style Conventions

### General Rules
- Always use explicit column aliases when performing transformations.
- Avoid using `.collect()` on large DataFrame partitions; use `.take(n)` or write to temporary storage.
- Prefer Delta Lake `MERGE INTO` over full table overwrites (`INSERT OVERWRITE`) for Silver/Gold updates.
- Include standard audit columns on all Medallion tables:
  - `_ingested_at` (`current_timestamp()`)
  - `_source_file` (`input_file_name()`)
  - `_updated_at` (`current_timestamp()`)

### Code Sample (PySpark Silver Transformation)

```python
from pyspark.sql import DataFrame
import pyspark.sql.functions as F


def transform_silver_customers(raw_df: DataFrame) -> DataFrame:
    """Cleans raw customer data from Oracle Fusion ERP.

    Applies string normalization, date formatting, and deduplication.
    """
    return (
        raw_df.filter(F.col("customer_id").isNotNull())
        .withColumn("first_name", F.trim(F.initcap(F.col("first_name"))))
        .withColumn("last_name", F.trim(F.initcap(F.col("last_name"))))
        .withColumn("email", F.lower(F.trim(F.col("email"))))
        .withColumn("_ingested_at", F.current_timestamp())
        .dropDuplicates(["customer_id"])
    )
```

---

## 4. Testing Framework (pytest & chispa)

Unit tests for PySpark transformations use `pytest` and `chispa` (for DataFrame assertion equality):

```bash
# Run test suite locally
pytest tests/
```

Example unit test (`tests/test_silver_customers.py`):

```python
from chispa.dataframe_comparer import assert_df_equality
from pyspark.sql import SparkSession
from notebooks.silver.transform_customers import transform_silver_customers


def test_transform_silver_customers(spark: SparkSession):
    input_data = [("101 ", "JOHN ", " John.Doe@Example.com ")]
    input_df = spark.createDataFrame(input_data, ["customer_id", "first_name", "email"])

    expected_data = [("101", "John", "john.doe@example.com")]

    result_df = transform_silver_customers(input_df)
    # Perform assertion checks
```

### Declarative manifests: pure-Python tests

PySpark DataFrame assertions (chispa) require a Spark runtime, which CI does not
provision. The declarative Bronze and Silver frameworks avoid this by keeping
every decision in a manifest and its validator, which are pure Python:

- `notebooks/shared/bronze_manifest.py`, `notebooks/shared/silver_manifest.py`, and
  `notebooks/shared/gold_manifest.py` load, validate, and resolve placeholders
  with no PySpark imports.
- `tests/test_bronze_manifest.py` pins the Energy Bronze manifest to the
  synthetic generator pack (entity coverage, primary keys) and exercises
  placeholder resolution for dev/qa/prod variables.
- `tests/test_silver_manifest.py` pins the Silver manifest to both the Bronze
  manifest (every source table exists) and the generator pack (SCD keys and
  conformed columns are actually generated), and validates the conforming-rule
  vocabulary. Both run on any Python 3.8+ with `pytest` — no Spark, no chispa.
- `tests/test_gold_manifest.py` pins the Gold manifest to the Silver manifest
  (every source exists) and the generator pack (primary keys, FK columns, and
  aggregated measures are generated), and unit-tests the generated date
  dimension. Same pure-Python constraint.
- `notebooks/shared/scd2.py` + `tests/test_scd2.py` pin the SCD Type 2
  semantics the Lakeflow engine must produce for `track_by` + `stored_as_scd_type=2` silver
  tables: initial version, close/open on tracked attribute changes, exactly
  one current version per key, no history growth for repeated identical
  records, and in-place absorption of untracked changes. The Lakeflow engine is
  the runtime implementation; the module is the reviewable oracle.

Spark-only helpers (`notebooks/shared/ingest.py`, `notebooks/shared/silver.py`,
`notebooks/shared/gold.py`) keep PySpark/Lakeflow imports inside functions so they
can be imported and linted without a runtime; they are reviewed statically and
validated against Databricks in Phase 5. Add a chispa job to CI when Spark
compute is available in the pipeline.
