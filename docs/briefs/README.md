# Feature Briefs

Every feature in this platform is documented as a consulting brief: the
**business problem** it solves, the **solution**, the **expected outcome**, and
how it is **implemented**. These briefs frame the engineering for stakeholders —
they answer *why* each capability exists, not just *how* it is built.

| Feature | Brief |
| ------- | ----- |
| Synthetic Enterprise Data Generator | [`sample-data/README.md`](../../sample-data/README.md) — deterministic, config-driven enterprise data that powers every pipeline offline. |
| Bronze Ingestion Framework | [bronze-ingestion-framework.md](bronze-ingestion-framework.md) — landing, raw ingestion, audit metadata, incremental processing. |
| Silver Conformed Layer | [silver-conformed-layer.md](silver-conformed-layer.md) — cleaning, normalization, deduplication, stable business keys. |
| Gold Star-Schema Layer | [gold-star-schema-layer.md](gold-star-schema-layer.md) — analytics-ready `dim_*` / `fact_*` models for BI. |

Each brief is written domain-agnostically; the Energy/Oil & Gas pack is the
reference implementation that demonstrates the platform. New industries
(Future: Retail, Healthcare, Manufacturing, Logistics, Finance) add manifests
and briefs without changing the framework.
