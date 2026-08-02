# Architecture Assets

Vector diagrams and diagram sources for the platform.

## Files

- [`exports/platform-architecture.svg`](exports/platform-architecture.svg) — canonical platform diagram. Color-scheme aware: renders correctly on GitHub light and dark themes. Embedded in the [README](../README.md).
- `exports/platform-architecture.png` — 2x rasterized fallback for contexts that do not render SVG. Regenerate from the SVG whenever the diagram changes.

## Source Layout

- `diagrams/` — Mermaid / PlantUML definitions (as produced).
- `drawio/` — Draw.io (Diagrams.net) XML sources for hand edits.
- `exports/` — generated SVG/PNG assets embedded in documentation.

The SVG in `exports/` is the single source of truth for the architecture graphic; keep other formats in sync when it changes.
