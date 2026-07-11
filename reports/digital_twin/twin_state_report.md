# Twin State Report

> **State management works correctly for synthetic data.** No real-world state transitions tested.

---

## State Representation

A twin state is a snapshot of climate variables at a location + timestamp:

```python
@dataclass
class TwinState:
    version_id: int            # Monotonically increasing
    location_id: str           # District name
    timestamp: datetime        # State timestamp
    state_type: StateType      # CURRENT | HISTORICAL | FORECAST | SCENARIO
    data: Dict[str, float]     # Climate variables
    parent_version: Optional[int]  # Previous version (for lineage)
    created_at: datetime       # When this state was created
    metadata: Dict             # Extra info (scenario_params, etc.)
```

---

## State Types

| Type | Description | Example |
|------|-------------|---------|
| CURRENT | Latest observed state | Today's weather (synthetic) |
| HISTORICAL | Past observed state | Last week's weather (synthetic) |
| FORECAST | Predicted future state | Next 7 days (from model on synthetic) |
| SCENARIO | What-if perturbation | +2°C scenario (delta from synthetic) |

---

## Versioning

```
Version 1 (CURRENT) → Version 2 (FORECAST) → Version 3 (SCENARIO)
                                                     │
                                          Version 4 (SCENARIO) [rollback illusion]
```

- Each version has a globally unique, monotonically increasing ID
- Parent references enable full lineage tracking
- Rollback creates a new version pointing to the desired state (no history destruction)
- All versions are immutable once created

---

## Persistence

| Format | Scheme | Example Path |
|--------|--------|-------------|
| Parquet | Per-location, partitioned by type | `data/twin/kalaburagi/current.parquet` |
| Metadata | JSON sidecar | `data/twin/kalaburagi/metadata.json` |

---

## State Reconciliation

When multiple updates arrive for the same location:

1. Each update creates a new version
2. Version ID check prevents stale writes
3. Last-write-wins with client-provided parent version

---

## Current Limitations

1. **Only synthetic data loaded.** No real-state transitions have been recorded.
2. **No cleanup policy.** Old versions accumulate indefinitely.
3. **No distributed locking.** Safe for single-process only.
4. **No event sourcing.** EventBus events are not persisted.
