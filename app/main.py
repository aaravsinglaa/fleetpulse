"""FleetPulse FastAPI application."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.database import FleetRepository
from app.diagnostics import diagnose_fleet, diagnose_vehicle
from app.simulator import VEHICLES, TelemetrySimulator

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RETENTION_HOURS = 24 * 7


def get_retention_hours(value: float | None = None) -> float:
    """Read and validate the telemetry retention period."""
    raw_value = (
        value
        if value is not None
        else os.getenv("FLEETPULSE_RETENTION_HOURS", str(DEFAULT_RETENTION_HOURS))
    )
    try:
        hours = float(raw_value)
    except (TypeError, ValueError) as error:
        raise ValueError("FLEETPULSE_RETENTION_HOURS must be a number") from error
    if hours <= 0:
        raise ValueError("FLEETPULSE_RETENTION_HOURS must be greater than zero")
    return hours


class TelemetryInput(BaseModel):
    """Validated reading accepted from a vehicle gateway or replay client."""

    vehicle_id: int = Field(gt=0)
    battery_pct: float = Field(ge=0, le=100)
    temperature_c: float = Field(ge=-50, le=150)
    speed_kph: float = Field(ge=0, le=300)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: Literal["external_api", "sensor_gateway", "csv_replay"] = "external_api"

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(UTC)


def create_app(
    database_path: str | Path | None = None,
    *,
    run_simulator: bool = True,
    retention_hours: float | None = None,
) -> FastAPI:
    path = database_path or os.getenv("FLEETPULSE_DB", BASE_DIR / "fleetpulse.db")
    repository = FleetRepository(path)
    retention = get_retention_hours(retention_hours)
    simulator = TelemetrySimulator(repository, retention_hours=retention)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        repository.initialize()
        repository.seed_vehicles(VEHICLES)
        repository.prune_readings_older_than(
            (datetime.now(UTC) - timedelta(hours=retention)).isoformat()
        )
        if repository.telemetry_count() == 0:
            simulator.seed_demo_readings()
        task = asyncio.create_task(simulator.run()) if run_simulator else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    application = FastAPI(
        title="FleetPulse",
        description="Real-time fleet telemetry and diagnostics demo",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.repository = repository
    application.state.retention_hours = retention
    application.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

    @application.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(BASE_DIR / "static" / "index.html")

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/vehicles")
    def list_vehicles(request: Request) -> list[dict]:
        vehicles = request.app.state.repository.list_vehicles()
        incidents = diagnose_fleet(vehicles)
        incident_types = {}
        for incident in incidents:
            incident_types.setdefault(incident["vehicle_id"], []).append(incident["type"])
        for vehicle in vehicles:
            vehicle["incidents"] = incident_types.get(vehicle["id"], [])
            vehicle["status"] = "alert" if vehicle["incidents"] else "healthy"
        return vehicles

    @application.get("/vehicles/{vehicle_id}")
    def get_vehicle(
        vehicle_id: int,
        request: Request,
        history: int = Query(default=30, ge=1, le=200),
    ) -> dict:
        vehicle = request.app.state.repository.get_vehicle(vehicle_id, history)
        if vehicle is None:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        latest = {**vehicle, **(vehicle["telemetry"][0] if vehicle["telemetry"] else {})}
        vehicle["incidents"] = diagnose_vehicle(latest) if vehicle["telemetry"] else []
        return vehicle

    @application.get("/incidents")
    def list_incidents(request: Request) -> list[dict]:
        return diagnose_fleet(request.app.state.repository.list_vehicles())

    @application.post("/telemetry", status_code=201)
    def ingest_telemetry(reading: TelemetryInput, request: Request) -> dict:
        repository = request.app.state.repository
        if not repository.vehicle_exists(reading.vehicle_id):
            raise HTTPException(status_code=404, detail="Vehicle not found")
        timestamp = reading.timestamp.isoformat()
        repository.insert_reading(
            reading.vehicle_id,
            reading.battery_pct,
            reading.temperature_c,
            reading.speed_kph,
            timestamp,
            reading.source,
        )
        vehicle = repository.get_vehicle(reading.vehicle_id, 1)
        accepted_reading = {
            "vehicle_id": reading.vehicle_id,
            "battery_pct": reading.battery_pct,
            "temperature_c": reading.temperature_c,
            "speed_kph": reading.speed_kph,
            "timestamp": timestamp,
            "source": reading.source,
        }
        submitted = {**vehicle, **accepted_reading}
        return {
            "accepted": True,
            "reading": accepted_reading,
            "incidents": diagnose_vehicle(submitted),
        }

    return application


app = create_app()
