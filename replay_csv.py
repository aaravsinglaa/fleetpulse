"""Import a recorded telemetry CSV into FleetPulse."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.database import FleetRepository
from app.replay import load_replay_rows
from app.simulator import VEHICLES


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay recorded telemetry into FleetPulse")
    parser.add_argument("csv_file", type=Path, help="CSV file containing telemetry readings")
    parser.add_argument("--database", type=Path, default=Path("fleetpulse.db"))
    parser.add_argument(
        "--keep-timestamps",
        action="store_true",
        help="Keep recorded timestamps instead of aligning the final reading to now",
    )
    args = parser.parse_args()

    repository = FleetRepository(args.database)
    repository.initialize()
    repository.seed_vehicles(VEHICLES)
    rows = load_replay_rows(args.csv_file, align_to_now=not args.keep_timestamps)
    unknown_ids = sorted({row[0] for row in rows if not repository.vehicle_exists(row[0])})
    if unknown_ids:
        raise SystemExit(f"Unknown vehicle IDs: {', '.join(map(str, unknown_ids))}")
    repository.insert_batch(rows)
    print(f"Imported {len(rows)} readings from {args.csv_file} into {args.database}")


if __name__ == "__main__":
    main()
