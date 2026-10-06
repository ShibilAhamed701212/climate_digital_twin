"""Tests for climatedt.integrity.twin_store_scanner."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from climatedt.integrity import twin_store_scanner as scanner


def _write_state(path: Path, **cols: object) -> str:
    pq.write_table(pa.table({k: [v] for k, v in cols.items()}), path)
    return str(path)


def _write_index(store: Path, rows: list[dict]) -> None:
    pq.write_table(pa.Table.from_pylist(rows), store / "version_index.parquet")


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "data" / "twin_store"
    path.mkdir(parents=True)
    return path


def test_missing_store_returns_zero_counts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    results = scanner.scan_twin_store()

    assert results["total_states"] == 0
    assert all(v == 0 for v in results.values())


def test_missing_version_index_returns_zero_counts(store: Path) -> None:
    assert scanner.scan_twin_store()["total_states"] == 0


def test_clean_store_has_no_findings(store: Path) -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    s1 = _write_state(store / "s1.parquet", authenticity="REAL", observation_id="obs-1")
    s2 = _write_state(store / "s2.parquet", authenticity="real", run_id="run-2")
    _write_index(
        store,
        [
            {
                "entity_id": "loc-1",
                "version_number": 1,
                "version_id": "v1",
                "file_path": s1,
                "created_at": t0,
                "parent_version_id": None,
            },
            {
                "entity_id": "loc-1",
                "version_number": 2,
                "version_id": "v2",
                "file_path": s2,
                "created_at": t0 + timedelta(hours=1),
                "parent_version_id": "v1",
            },
        ],
    )

    results = scanner.scan_twin_store(verbose=True)

    assert results["total_states"] == 2
    assert results["real_states"] == 2
    for key in (
        "contaminated_states",
        "invalid_authenticity",
        "broken_parent_links",
        "duplicate_versions",
        "timestamp_inversions",
        "missing_provenance",
        "corrupt_records",
    ):
        assert results[key] == 0, key


def test_detects_every_finding_type(store: Path) -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    real = _write_state(store / "real.parquet", authenticity="REAL", observation_id="o")
    scen = _write_state(store / "scen.parquet", authenticity="SCENARIO", observation_id="o")
    noprov = _write_state(store / "noprov.parquet", authenticity="REAL")
    empty = store / "empty.parquet"
    pq.write_table(pa.table({"authenticity": pa.array([], type=pa.string())}), empty)
    rows = [
        # v1 then a duplicate v1
        {"entity_id": "a", "version_number": 1, "version_id": "a1", "file_path": real},
        {"entity_id": "a", "version_number": 1, "version_id": "a1b", "file_path": real},
        # contaminated scenario state with a parent that does not exist
        {
            "entity_id": "b",
            "version_number": 1,
            "version_id": "b1",
            "file_path": scen,
            "parent_version_id": "ghost",
        },
        # v2 created before v1 -> timestamp inversion; no provenance
        {"entity_id": "c", "version_number": 1, "version_id": "c1", "file_path": real},
        {"entity_id": "c", "version_number": 2, "version_id": "c2", "file_path": noprov},
        # empty and unreadable state files
        {"entity_id": "d", "version_number": 1, "version_id": "d1", "file_path": str(empty)},
        {
            "entity_id": "e",
            "version_number": 1,
            "version_id": "e1",
            "file_path": str(store / "missing.parquet"),
        },
    ]
    times = {("c", 1): t0 + timedelta(days=1), ("c", 2): t0}
    for r in rows:
        r["created_at"] = times.get((r["entity_id"], r["version_number"]), t0)
        r.setdefault("parent_version_id", None)
    _write_index(store, rows)

    results = scanner.scan_twin_store(verbose=True)

    assert results["total_states"] == 7
    assert results["duplicate_versions"] == 1
    assert results["invalid_authenticity"] == 1
    assert results["contaminated_states"] == 1
    assert results["broken_parent_links"] == 1
    assert results["timestamp_inversions"] == 1
    assert results["missing_provenance"] == 1
    assert results["corrupt_records"] == 2
    # Only REAL states are counted as real (the SCENARIO state is not).
    assert results["real_states"] == 4


def test_main_exits_nonzero_when_issues_found(store: Path, monkeypatch, capsys) -> None:
    scen = _write_state(store / "scen.parquet", authenticity="SIMULATED", run_id="r")
    _write_index(
        store,
        [
            {
                "entity_id": "x",
                "version_number": 1,
                "version_id": "x1",
                "file_path": scen,
                "created_at": datetime(2026, 1, 1, tzinfo=UTC),
                "parent_version_id": None,
            }
        ],
    )
    monkeypatch.setattr("sys.argv", ["scanner"])

    with pytest.raises(SystemExit) as exc:
        scanner.main()

    assert exc.value.code == 1
    assert "ISSUES FOUND" in capsys.readouterr().out


def test_main_reports_verified_for_empty_store(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["scanner", "--verbose"])

    scanner.main()

    assert "TWIN STORE INTEGRITY VERIFIED" in capsys.readouterr().out
