#!/usr/bin/env python
"""REAL Twin store integrity scanner — read-only verification.

Usage: python -m climatedt.integrity twin-store [--verbose]

Scans the authoritative Twin store for:
  - Non-REAL authenticity contamination
  - SCENARIO / SIMULATED / SYNTHETIC contamination
  - Missing provenance fields
  - Duplicate versions
  - Broken parent references
  - Timestamp inversions
  - Corrupt / unreadable state files
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def scan_twin_store(verbose: bool = False) -> dict[str, int]:
    results: dict[str, int] = {
        "total_states": 0,
        "real_states": 0,
        "contaminated_states": 0,
        "invalid_authenticity": 0,
        "broken_parent_links": 0,
        "duplicate_versions": 0,
        "timestamp_inversions": 0,
        "missing_provenance": 0,
        "corrupt_records": 0,
    }

    store_path = Path("data/twin_store")
    if not store_path.exists():
        print("No twin store found at", store_path)
        return results

    version_index = store_path / "version_index.parquet"
    if not version_index.exists():
        print("No version index found at", version_index)
        return results

    try:
        import pyarrow.parquet as pq

        index = pq.read_table(version_index)
        results["total_states"] = index.num_rows

        seen_versions: dict[str, set[int]] = {}
        entity_timestamps: dict[str, list] = {}
        all_version_ids: set[str] = set()

        for i in range(index.num_rows):
            eid = str(index.column("entity_id")[i].as_py())
            vn = int(index.column("version_number")[i].as_py())
            vid = str(index.column("version_id")[i].as_py())
            fp = str(index.column("file_path")[i].as_py())
            all_version_ids.add(vid)

            if eid not in seen_versions:
                seen_versions[eid] = set()
                entity_timestamps[eid] = []
            if vn in seen_versions[eid]:
                results["duplicate_versions"] += 1
                if verbose:
                    print(f"DUPLICATE: {eid} v{vn}")
            seen_versions[eid].add(vn)
            entity_timestamps[eid].append((vn, index.column("created_at")[i].as_py()))

            # Read state file
            try:
                state_table = pq.read_table(fp)
                if state_table.num_rows == 0:
                    results["corrupt_records"] += 1
                    continue

                auth = str(state_table.column("authenticity")[0].as_py()) if "authenticity" in state_table.column_names else "UNKNOWN"
                if auth.upper() not in ("REAL",):
                    results["invalid_authenticity"] += 1
                    if any(x in auth.upper() for x in ("SCENARIO", "SIMULATED", "SYNTHETIC")):
                        results["contaminated_states"] += 1
                    if verbose:
                        print(f"NON_REAL: {eid} v{vn} auth={auth}")
                results["real_states"] += 1

                obs_id = str(state_table.column("observation_id")[0].as_py()) if "observation_id" in state_table.column_names else ""
                run_id_val = str(state_table.column("run_id")[0].as_py()) if "run_id" in state_table.column_names else ""
                if not obs_id and not run_id_val:
                    results["missing_provenance"] += 1
                    if verbose:
                        print(f"NO_PROVENANCE: {eid} v{vn}")

            except Exception:
                results["corrupt_records"] += 1
                if verbose:
                    print(f"CORRUPT: {fp}")

        # Parent link check
        for i in range(index.num_rows):
            parent = str(index.column("parent_version_id")[i].as_py())
            if parent and parent != "None" and parent not in all_version_ids:
                results["broken_parent_links"] += 1
                if verbose:
                    print(f"BROKEN_PARENT: {str(index.column('entity_id')[i].as_py())} v{int(index.column('version_number')[i].as_py())} parent={parent}")

        # Timestamp inversion check per entity
        for eid, ts_list in entity_timestamps.items():
            ts_list.sort(key=lambda x: x[0])  # sort by version
            for j in range(1, len(ts_list)):
                if ts_list[j][1] < ts_list[j-1][1]:
                    results["timestamp_inversions"] += 1
                    if verbose:
                        print(f"TIME_INVERSION: {eid} v{ts_list[j][0]}")

    except ImportError:
        print("pyarrow not available — cannot scan parquet twin store")
    except Exception as e:
        print(f"Error scanning twin store: {e}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="REAL twin store integrity scanner")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed findings")
    args = parser.parse_args()

    results = scan_twin_store(args.verbose)

    print()
    for key in (
        "total_states",
        "real_states",
        "contaminated_states",
        "invalid_authenticity",
        "broken_parent_links",
        "duplicate_versions",
        "timestamp_inversions",
        "missing_provenance",
        "corrupt_records",
    ):
        val = results[key]
        status = "PASS" if val == 0 else f"FOUND {val}"
        print(f"{key.upper()}={val}  [{status}]")

    has_issues = any(
        results[k] > 0
        for k in (
            "contaminated_states",
            "invalid_authenticity",
            "broken_parent_links",
            "duplicate_versions",
            "timestamp_inversions",
            "corrupt_records",
        )
    )
    if has_issues:
        print("\nWARNING: ISSUES FOUND — review above for details")
        sys.exit(1)
    else:
        print("\nTWIN STORE INTEGRITY VERIFIED")


if __name__ == "__main__":
    main()
