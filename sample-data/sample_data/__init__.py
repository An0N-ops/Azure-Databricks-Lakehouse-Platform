"""Synthetic Enterprise Data Generator.

Deterministic, config-driven generator for domain-specific sample data. The
generator core is domain-agnostic; industry packs (e.g. ``industries/energy``)
define entities, relationships, and volumes as JSON so downstream Bronze/Silver
ingestion can be developed without real or PII-bearing data.
"""

__version__ = "0.1.0"
