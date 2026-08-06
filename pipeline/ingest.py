#!/usr/bin/env python3
"""Phase 1 — Real Data Ingestion Pipeline.

Authoritative CLI entry point for ingesting real climate observations from
external providers (Open-Meteo, NASA POWER, IMD).

Usage:
    python -m pipeline.ingest --help
    python -m pipeline.ingest --provider open_meteo --lat 12.9716 --lon 77.5946
    python -m pipeline.ingest --intent forecast --provider open_meteo
    python -m pipeline.ingest --provider nasa_power --intent historical
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from pipeline.ingestion_service import IngestionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
_logger = logging.getLogger("pipeline.ingest")

PROVIDER_CHOICES = ["auto", "open_meteo", "nasa_power", "imd"]
INTENT_CHOICES = ["recent", "historical", "forecast", "auto"]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest real climate observations from external providers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--lat", type=float, default=12.9716, help="Latitude (default: 12.9716, Bengaluru)"
    )
    parser.add_argument(
        "--lon", type=float, default=77.5946, help="Longitude (default: 77.5946, Bengaluru)"
    )
    parser.add_argument(
        "--intent",
        choices=INTENT_CHOICES,
        default="recent",
        help="Type of data to fetch (default: recent)",
    )
    parser.add_argument(
        "--provider",
        choices=PROVIDER_CHOICES,
        default="auto",
        help="Provider override (default: auto-resolve)",
    )
    parser.add_argument(
        "--demo-synthetic",
        action="store_true",
        help="Allow synthetic data generation (test/demo only)",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument("--verbose", action="store_true", help="Detailed logging")
    return parser.parse_args(argv)


def _print_text(result: dict) -> None:
    status = result.get("status", "UNKNOWN")
    print()
    print("+" + "-" * 50 + "+")
    print(f"|  Ingestion Run: {result.get('run_id', '?'):<36} |")
    print("|" + "-" * 50 + "|")
    if status == "SUCCESS":
        print(f"|  Provider:        {str(result.get('provider', '?')):<30} |")
        print(f"|  Source Dataset:  {str(result.get('source_dataset', '?')):<30} |")
        print(f"|  Authenticity:    {str(result.get('authenticity', '?')):<30} |")
        print(f"|  Status:          {str(result.get('status', '?')):<30} |")
        print(
            f"|  Location:        {result.get('latitude', '?'):<8} {result.get('longitude', '?'):<8}             |"
        )
        print("|                                                  |")
        ts = result.get("observation_timestamp", "")
        print(f"|  Observation:     {ts:<35} |")
        ing = result.get("ingestion_timestamp", "")
        print(f"|  Ingestion:       {ing:<35} |")
        print("|                                                  |")
        for var, val in result.get("values", {}).items():
            unit = result.get("units", {}).get(var, "")
            print(f"|  {var:<18} {val:>8} {unit:<10} |")
        print("|                                                  |")
        print(
            f"|  Records:         {result.get('records_received', 0):>3} received, {result.get('records_validated', 0):>3} validated, {result.get('records_rejected', 0):>3} rejected |"
        )
        print(
            f"|  Synthetic:       {result.get('synthetic_count', 0):>3}                                      |"
        )
        print("|                                                  |")
        print("|  Saved:                                          |")
        for key, path in (result.get("paths") or {}).items():
            if path:
                p = str(path)[:50]
                print(f"|    {p:<51}|")
    else:
        print(f"|  Error:           {str(result.get('error', 'Unknown')):<32} |")
    print("+" + "-" * 50 + "+")
    print()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.verbose:
        logging.getLogger("pipeline").setLevel(logging.DEBUG)

    override = None if args.provider == "auto" else args.provider
    intent = args.intent if args.intent != "auto" else "recent"

    service = IngestionService()
    result = service.run_single(
        lat=args.lat,
        lon=args.lon,
        intent=intent,
        provider_override=override,
    )

    if args.output == "json":
        print(json.dumps(result, indent=2, default=str))
    else:
        _print_text(result)

    return 0 if result.get("status") == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
