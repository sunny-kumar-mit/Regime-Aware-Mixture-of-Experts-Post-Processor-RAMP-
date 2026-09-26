#!/usr/bin/env python3
"""
RAMP Data Layer CLI Tool
SIH26080 | Command-line interface for data ingestion management

Usage:
  python -m scripts.ramp_data status
  python -m scripts.ramp_data providers
  python -m scripts.ramp_data validate <provider_id>
  python -m scripts.ramp_data manifest
  python -m scripts.ramp_data init-dirs
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from project root: python scripts/ramp_data.py <cmd>
_HERE = Path(__file__).resolve().parent
_BACKEND_SRC = _HERE.parent / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))


def cmd_status(args: argparse.Namespace) -> None:
    """Show overall data layer status."""
    from ramp.ingestion.registry import get_registry

    registry = get_registry()
    infos = registry.list_all_providers()

    available = [p for p in infos if p.status.value == "AVAILABLE"]
    unavailable = [p for p in infos if p.status.value in ("NOT_CONFIGURED", "UNAVAILABLE")]

    print("\n═══════════════════════════════════════════════")
    print("  RAMP Phase 2 — Data Layer Status")
    print("═══════════════════════════════════════════════")
    print(f"  Total providers: {len(infos)}")
    print(f"  Available:       {len(available)}")
    print(f"  Not configured:  {len(unavailable)}")
    print("")

    for p in infos:
        icon = "✅" if p.status.value == "AVAILABLE" else "⚠️ " if p.status.value == "CONFIGURED" else "❌"
        print(f"  {icon} [{p.provider_type.value:12s}] {p.provider_id:25s} {p.status.value}")

    # Overall readiness
    nwp_ok = any(p.status.value == "AVAILABLE" and p.provider_type.value == "nwp" for p in infos)
    obs_ok = any(p.status.value == "AVAILABLE" and p.provider_type.value == "observation" for p in infos)
    ready = nwp_ok and obs_ok

    print("")
    status_str = "READY" if ready else "NOT READY"
    print(f"  Pipeline status: {'✅ ' + status_str if ready else '❌ ' + status_str}")
    if not nwp_ok:
        print("  → Add GFS/GEFS GRIB2 files to data/raw/nwp/ to enable NWP providers")
    if not obs_ok:
        print("  → Add IMD NetCDF files to data/raw/observations/imd/ to enable observations")
    print("")


def cmd_providers(args: argparse.Namespace) -> None:
    """List all providers with details."""
    from ramp.ingestion.registry import get_registry

    registry = get_registry()
    infos = registry.list_all_providers()

    print("\n RAMP Registered Data Providers\n")
    for p in infos:
        print(f"  ─────────────────────────────────────────")
        print(f"  ID:          {p.provider_id}")
        print(f"  Name:        {p.name}")
        print(f"  Type:        {p.provider_type.value}")
        print(f"  Status:      {p.status.value}")
        print(f"  Resolution:  {p.spatial_resolution_deg}°")
        print(f"  Variables:   {', '.join(p.available_variables[:6])}{'...' if len(p.available_variables) > 6 else ''}")
        if p.notes:
            print(f"  Notes:       {p.notes[:100]}")
        print("")


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate a specific provider and print report."""
    from ramp.ingestion.registry import get_registry

    registry = get_registry()
    provider = registry.get_nwp(args.provider_id) or registry.get_obs(args.provider_id)

    if provider is None:
        print(f"ERROR: Provider '{args.provider_id}' not found.")
        print(f"Available: {[p.provider_id for p in registry.list_all_providers()]}")
        sys.exit(1)

    print(f"\nValidating provider: {args.provider_id}")
    report = provider.validate_source()

    print(f"  Dataset:  {report.dataset_name}")
    print(f"  Passed:   {'✅ YES' if report.passed else '❌ NO'}")
    print(f"  Timesteps: {report.n_timesteps}")
    print(f"  Data mode: {report.data_mode.value}")

    if report.errors:
        print("\n  ERRORS:")
        for e in report.errors:
            print(f"    ❌ {e}")

    if report.warnings:
        print("\n  WARNINGS:")
        for w in report.warnings:
            print(f"    ⚠️  {w}")

    if report.notes:
        print(f"\n  NOTES: {report.notes}")

    # Optionally save report
    if args.save:
        from ramp.validation.report import save_validation_report

        out_dir = Path("data/metadata/validation")
        json_path, md_path = save_validation_report(report, out_dir)
        print(f"\n  Saved: {json_path}")
        print(f"         {md_path}")

    print("")


def cmd_manifest(args: argparse.Namespace) -> None:
    """Show or (re)build the data manifest."""
    from ramp.validation.manifest import load_manifest, save_manifest

    manifest = load_manifest()

    if args.rebuild:
        from ramp.validation.manifest import _build_default_manifest
        manifest = _build_default_manifest()
        save_manifest(manifest)
        print("✅ Rebuilt default data manifest.")

    print(f"\n RAMP Data Manifest (v{manifest.version})")
    print(f" Generated: {manifest.generated_at}")
    print(f" Datasets: {len(manifest.datasets)}\n")

    for ds in manifest.datasets:
        icon = "✅" if ds.status == "AVAILABLE" else "❌"
        print(f"  {icon} {ds.id:25s} [{ds.status:15s}] {ds.provider}")


def cmd_init_dirs(args: argparse.Namespace) -> None:
    """Create the full data directory structure."""
    dirs = [
        "data/raw/nwp/gfs",
        "data/raw/nwp/gefs",
        "data/raw/nwp/ncmrwf/ncum",
        "data/raw/nwp/ncmrwf/neps",
        "data/raw/observations/imd",
        "data/raw/auxiliary/dem",
        "data/raw/auxiliary/shapefiles",
        "data/interim/normalized",
        "data/interim/regridded",
        "data/interim/aligned",
        "data/processed/features",
        "data/processed/training",
        "data/metadata/datasets",
        "data/metadata/schemas",
        "data/metadata/validation",
        "data/cache",
    ]
    for d in dirs:
        path = Path(d)
        path.mkdir(parents=True, exist_ok=True)
        # Add .gitkeep to track empty dirs
        gitkeep = path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text(
                "# This directory is tracked by git.\n"
                "# Place data files here as described in docs/DATA_ARCHITECTURE.md\n"
            )
    print(f"✅ Initialized {len(dirs)} data directories.")

    # Build initial manifest
    from ramp.validation.manifest import _build_default_manifest, save_manifest
    manifest = _build_default_manifest()
    save_manifest(manifest)
    print("✅ Created default data_manifest.json")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ramp_data",
        description="RAMP Phase 2 Data Layer CLI (SIH26080)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show data layer readiness status")
    subparsers.add_parser("providers", help="List all data providers with details")

    validate_parser = subparsers.add_parser("validate", help="Validate a specific provider")
    validate_parser.add_argument("provider_id", help="Provider ID to validate")
    validate_parser.add_argument("--save", action="store_true", help="Save validation report to disk")

    manifest_parser = subparsers.add_parser("manifest", help="Show or rebuild the data manifest")
    manifest_parser.add_argument("--rebuild", action="store_true", help="Rebuild default manifest")

    subparsers.add_parser("init-dirs", help="Initialize the data directory structure")

    args = parser.parse_args()

    commands = {
        "status": cmd_status,
        "providers": cmd_providers,
        "validate": cmd_validate,
        "manifest": cmd_manifest,
        "init-dirs": cmd_init_dirs,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
