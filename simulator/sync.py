from __future__ import annotations

import argparse
import json
import logging
import sys

from pipeline.stores.observation_store import ObservationStore
from simulator.synchronizer.sync_result import SyncResult
from simulator.synchronizer.twin_health import get_all_twin_health, get_twin_health
from simulator.synchronizer.twin_sync_service import TwinSyncService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
_logger = logging.getLogger("simulator.sync")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronize real observations into the Digital Twin.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--location", type=str, default="", help="Location ID to sync (e.g., KA-BLR)"
    )
    parser.add_argument(
        "--provider", type=str, default="", help="Filter by provider (e.g., open_meteo)"
    )
    parser.add_argument("--sync-only", action="store_true", help="Sync pending observations only")
    parser.add_argument("--health", type=str, default="", help="Check health for a location")
    parser.add_argument("--health-all", action="store_true", help="Check health for all locations")
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument("--verbose", action="store_true", help="Detailed logging")
    return parser.parse_args(argv)


def _print_results(results: list[SyncResult]) -> None:
    for r in results:
        print()
        print("+" + "-" * 60 + "+")
        print(f"|  Status:          {r.status:<42} |")
        print(f"|  Location:        {r.location_id:<42} |")
        if r.observation_id:
            print(f"|  Observation ID:  {r.observation_id:<42} |")
        if r.run_id:
            print(f"|  Run ID:          {r.run_id:<42} |")
        if r.provider:
            print(f"|  Provider:        {r.provider:<42} |")
        if r.authenticity:
            print(f"|  Authenticity:    {r.authenticity:<42} |")
        if r.old_version > 0:
            print(f"|  Old Version:     {r.old_version:<42} |")
        if r.new_version > 0:
            print(f"|  New Version:     {r.new_version:<42} |")
        if r.changed_variables:
            print(f"|  Changed:         {', '.join(r.changed_variables):<42} |")
        if r.error:
            print(f"|  Error:           {r.error:<42} |")
        print("+" + "-" * 60 + "+")
        print()


def _print_freshness(f: dict) -> None:
    print()
    print("+" + "-" * 60 + "+")
    print(f"|  Location:        {str(f.get('location_id', '?')):<42} |")
    print(f"|  Status:          {str(f.get('status', '?')):<42} |")
    print(f"|  Freshness:       {str(f.get('freshness', '?')):<42} |")
    print(f"|  Version:         {str(f.get('latest_version', '?')):<42} |")
    print(f"|  Provider:        {str(f.get('provider', '?')):<42} |")
    print(f"|  Authenticity:    {str(f.get('authenticity', '?')):<42} |")
    print(f"|  Last Obs At:     {str(f.get('latest_observation_at', '?')):<42} |")
    print("+" + "-" * 60 + "+")
    print()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.verbose:
        logging.getLogger("simulator").setLevel(logging.DEBUG)

    if args.health:
        f = get_twin_health(args.health)
        if args.output == "json":
            print(json.dumps(f, indent=2, default=str))
        else:
            _print_freshness(f)
        return 0

    if args.health_all:
        results = get_all_twin_health()
        if args.output == "json":
            print(json.dumps(results, indent=2, default=str))
        else:
            for f in results:
                _print_freshness(f)
        return 0

    service = TwinSyncService()
    obs_store = ObservationStore()

    if args.sync_only:
        results = service.sync_pending_observations(obs_store, location_id=args.location or None)
    else:
        all_obs = obs_store.query()
        results = []
        for obs in all_obs:
            if args.provider and obs.provider != args.provider:
                continue
            loc = args.location or None
            results.append(service.sync_from_observation(obs, location_id=loc))

    if args.output == "json":
        data = []
        for r in results:
            d = {
                "status": r.status,
                "location_id": r.location_id,
                "observation_id": r.observation_id,
                "run_id": r.run_id,
                "provider": r.provider,
                "authenticity": r.authenticity,
                "old_version": r.old_version,
                "new_version": r.new_version,
                "changed_variables": r.changed_variables,
                "error": r.error,
            }
            data.append(d)
        print(json.dumps(data, indent=2, default=str))
    else:
        _print_results(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
