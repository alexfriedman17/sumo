from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import run_validation_stage, validate_existing


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Historical sumo data ingestion pipeline")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Workspace root containing the Old Data folder.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory for raw cache, SQLite database, and exports.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("run-validation", "download"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--start-year", type=int, default=2025)
        sub.add_argument("--end-year", type=int, default=2026)
        sub.add_argument("--division", default="Makuuchi")
        sub.add_argument("--include-future", action="store_true")
        sub.add_argument("--force", action="store_true")
        sub.add_argument("--fetch-jsa-profiles", action="store_true")
        sub.add_argument("--polite-delay", type=float, default=0.2)

    subparsers.add_parser("validate")

    args = parser.parse_args(argv)
    project_root = args.project_root.resolve()
    data_dir = (project_root / args.data_dir).resolve() if not args.data_dir.is_absolute() else args.data_dir

    if args.command in {"run-validation", "download"}:
        summary = run_validation_stage(
            project_root,
            data_dir=data_dir,
            start_year=args.start_year,
            end_year=args.end_year,
            division=args.division,
            include_future=args.include_future,
            force=args.force,
            fetch_jsa_profiles=args.fetch_jsa_profiles,
            polite_delay=args.polite_delay,
        )
        print("Sumo data ingestion complete")
        print(f"Bashos attempted: {summary.bashos_attempted}")
        print(f"Torikumi rows loaded: {summary.torikumi_rows}")
        print(f"Banzuke rows loaded: {summary.banzuke_rows}")
        print(f"Wrestlers fetched: {summary.wrestlers_fetched}")
        print(f"JSA profiles cached: {summary.jsa_profiles_fetched}")
        print(f"SQLite database: {summary.database_path}")
        print(f"Validation exports: {summary.exports_dir}")
        return

    if args.command == "validate":
        exports_dir = validate_existing(project_root, data_dir=data_dir)
        print(f"Validation exports refreshed: {exports_dir}")
        return

    parser.error(f"Unhandled command: {args.command}")
