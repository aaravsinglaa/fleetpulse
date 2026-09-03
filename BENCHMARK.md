# FleetPulse benchmark

Measured on September 3, 2026 using Python 3.14.7 and SQLite on the local development machine.

## Result

The median of five runs for inserting **10,000 synthetic telemetry readings** in one SQLite transaction and then loading the latest state for all 10 vehicles and evaluating fleet diagnostic rules was **9.7 ms**, or approximately **1.03 million readings/second**.

Individual runs: 10.0 ms, 9.5 ms, 10.0 ms, 9.7 ms, and 9.4 ms.

## Reproduce

```bash
source .venv/bin/activate
python benchmark.py
```

Each timed run creates a fresh temporary on-disk SQLite database with WAL mode and the production index, inserts a prebuilt batch, reads the latest fleet state, runs diagnostics, and verifies the row count. Data generation, schema creation, and vehicle seeding are intentionally outside the timed region. This is a local batch-ingestion measurement, not a claim about HTTP request throughput or production-scale infrastructure.
