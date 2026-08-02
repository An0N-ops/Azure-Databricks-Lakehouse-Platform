"""Command-line entry point for the Synthetic Enterprise Data Generator.

Example:
    python -m sample_data generate --industry energy --seed 42 --scale 0.1
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sample_data import __version__
from sample_data.config import load_config
from sample_data.engine import generate
from sample_data.errors import ConfigError
from sample_data.writers import write_batch

DEFAULT_CONFIG_DIR = str(Path(__file__).resolve().parent / "industries")
DEFAULT_OUTPUT_DIR = str(Path.cwd() / "sample-data" / "output")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sample_data",
        description="Synthetic Enterprise Data Generator (config-driven, deterministic).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available industry packs")
    list_parser.add_argument("--config-dir", default=DEFAULT_CONFIG_DIR)

    gen_parser = subparsers.add_parser(
        "generate", help="Generate a batch of synthetic data for an industry pack"
    )
    gen_parser.add_argument("--industry", default="energy", help="Industry pack name")
    gen_parser.add_argument("--config-dir", default=DEFAULT_CONFIG_DIR)
    gen_parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR)
    gen_parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    gen_parser.add_argument("--start-date", help="Generation window start (YYYY-MM-DD)")
    gen_parser.add_argument("--end-date", help="Generation window end (YYYY-MM-DD)")
    gen_parser.add_argument("--as-of-date", help="Batch/ingestion date (YYYY-MM-DD), default today")
    gen_parser.add_argument("--scale", type=float, default=1.0, help="Scale volumes (default: 1.0)")
    gen_parser.add_argument("--format", choices=["csv", "json"], default="csv")
    gen_parser.add_argument("--parquet", action="store_true", help="Also write Parquet files")
    return parser


def main(argv: list | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "list":
            return _list_industries(Path(args.config_dir))
        return _generate(args)
    except (ConfigError, OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _list_industries(config_dir: Path) -> int:
    config_dir = Path(config_dir)
    if not config_dir.is_dir():
        raise ConfigError(f"config dir not found: {config_dir}")
    packs = sorted(path.parent.name for path in config_dir.glob("*/config.json"))
    if not packs:
        print(f"no industry packs found under {config_dir}")
        return 1
    print("Available industry packs:")
    for pack in packs:
        print(f"  - {pack}")
    return 0


def _generate(args: argparse.Namespace) -> int:
    config_path = Path(args.config_dir) / args.industry / "config.json"
    config = load_config(config_path)
    metadata = config["metadata"]
    industry = metadata["industry"]

    start_date = _parse_optional_date(args.start_date, "start-date")
    end_date = _parse_optional_date(args.end_date, "end-date")
    as_of_date = (
        _parse_optional_date(args.as_of_date, "as-of-date")
        or datetime.now(
            timezone.utc  # noqa: UP017
        ).date()
    )
    if isinstance(as_of_date, str):
        as_of_date = date.fromisoformat(as_of_date)
    if args.scale <= 0:
        raise ValueError("--scale must be > 0")

    data = generate(
        config,
        seed=args.seed,
        start_date=start_date,
        end_date=end_date,
        scale=args.scale,
    )

    bounds = _effective_bounds(config, start_date, end_date)
    files, manifest = write_batch(
        Path(args.output),
        industry,
        data,
        seed=args.seed,
        as_of_date=as_of_date,
        start_date=bounds[0],
        end_date=bounds[1],
        scale=args.scale,
        metadata=metadata,
        fmt=args.format,
        parquet=args.parquet,
    )

    total = sum(manifest["entity_counts"].values())
    print(
        f"Generated {len(data)} entities / {total:,} rows for '{industry}' "
        f"into {Path(args.output) / industry}"
    )
    print(f"Wrote {len(files)} files (seed={args.seed}, scale={args.scale})")
    return 0


def _parse_optional_date(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid --{label} '{value}' (expected YYYY-MM-DD)") from exc
    return value


def _effective_bounds(config, start_date: str | None, end_date: str | None):
    metadata = config.get("metadata", {})
    start = start_date or metadata.get("default_start_date")
    end = end_date or metadata.get("default_end_date")
    start_obj = date.fromisoformat(start)
    end_obj = date.fromisoformat(end)
    return start_obj, end_obj
