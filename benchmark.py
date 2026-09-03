"""Repeatable local batch-ingestion benchmark for the resume-ready project."""

from __future__ import annotations

import statistics
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.database import FleetRepository
from app.diagnostics import diagnose_fleet
from app.simulator import VEHICLES

BATCH_SIZE = 10_000
RUNS = 5


def make_rows():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        (
            index % 10 + 1,
            90 - index % 40,
            53.0 if index % 97 == 0 else 30.0 + index % 15,
            float(index % 90),
            (start + timedelta(milliseconds=index)).isoformat(),
            "simulator",
        )
        for index in range(BATCH_SIZE)
    ]


def run_once(rows) -> tuple[float, int]:
    with tempfile.TemporaryDirectory() as directory:
        repository = FleetRepository(Path(directory) / "benchmark.db")
        repository.initialize()
        repository.seed_vehicles(VEHICLES)
        started = time.perf_counter()
        repository.insert_batch(rows)
        incidents = diagnose_fleet(repository.list_vehicles(), now=datetime(2026, 1, 1, 0, 0, 10, tzinfo=timezone.utc))
        elapsed = time.perf_counter() - started
        assert repository.telemetry_count() == BATCH_SIZE
        return elapsed, len(incidents)


if __name__ == "__main__":
    rows = make_rows()
    timings = [run_once(rows)[0] for _ in range(RUNS)]
    median = statistics.median(timings)
    print(f"Batch: {BATCH_SIZE:,} readings + fleet diagnostics")
    print(f"Runs: {RUNS}")
    print(f"Median: {median * 1000:.1f} ms")
    print(f"Throughput: {BATCH_SIZE / median:,.0f} readings/second")
    print("All timings: " + ", ".join(f"{value * 1000:.1f} ms" for value in timings))
