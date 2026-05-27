"""Behavioral tests for export service correctness and responsiveness."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import threading
import time
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient


APP_FILE_PATH = Path("/app/main.py")


def load_app_module():
    """Load /app/main.py as a Python module for runtime behavior checks."""
    module_spec = importlib.util.spec_from_file_location("target_app", APP_FILE_PATH)
    assert module_spec and module_spec.loader, (
        "Could not load module spec from /app/main.py"
    )

    app_module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(app_module)
    return app_module


def test_contract_file_present():
    """The target application file should exist after setup or solution."""
    assert APP_FILE_PATH.exists(), "Expected /app/main.py to exist"


def test_contract_health_payload():
    """Health endpoint should stay available and return the expected payload."""
    module = load_app_module()
    client = TestClient(module.app)

    response = client.get("/health")
    assert response.status_code == 200, "Expected /health to return HTTP 200"
    assert response.json() == {"status": "ok"}, "Unexpected /health payload"


def test_contract_bulk_export_shape_and_types():
    """Export response should match schema, include checksum, and use UTC timestamp."""
    module = load_app_module()
    client = TestClient(module.app)

    response = client.get("/bulk-export")
    assert response.status_code == 200, "Expected /bulk-export to return HTTP 200"

    payload = response.json()
    expected_keys = {
        "filename",
        "rows",
        "bytes",
        "checksum_sha256",
        "generated_at",
    }
    assert set(payload.keys()) == expected_keys, "Unexpected export response keys"
    assert payload["filename"] == "bulk-export.csv", "filename contract mismatch"
    assert isinstance(payload["rows"], int) and payload["rows"] == 1200
    assert isinstance(payload["bytes"], int) and payload["bytes"] > 0
    assert isinstance(payload["checksum_sha256"], str)
    assert len(payload["checksum_sha256"]) == 64

    parsed = datetime.fromisoformat(payload["generated_at"])
    assert parsed.tzinfo is not None, "generated_at must include timezone"
    assert payload["generated_at"].endswith("+00:00"), "generated_at must be UTC"


def test_contract_rows_parameter_and_validation_edges():
    """Query validation should enforce bounds while allowing valid values."""
    module = load_app_module()
    client = TestClient(module.app)

    response = client.get("/bulk-export", params={"rows": 2500})
    assert response.status_code == 200
    assert response.json()["rows"] == 2500

    too_small = client.get("/bulk-export", params={"rows": 9})
    assert too_small.status_code == 422

    too_large = client.get("/bulk-export", params={"rows": 5001})
    assert too_large.status_code == 422


def test_contract_checksum_matches_generated_bytes():
    """Reported checksum and byte count must correspond to generated CSV bytes."""
    module = load_app_module()
    client = TestClient(module.app)

    original = module.legacy_generate_csv
    csv_text = "id,user,message\n1,user-1,hello\n2,user-2,world\n"

    def deterministic_csv(rows: int = 1200) -> str:
        return csv_text

    module.legacy_generate_csv = deterministic_csv
    try:
        response = client.get("/bulk-export", params={"rows": 12})
        assert response.status_code == 200
        payload = response.json()
        expected_bytes = csv_text.encode("utf-8")
        assert payload["bytes"] == len(expected_bytes)
        assert payload["checksum_sha256"] == hashlib.sha256(expected_bytes).hexdigest()
        assert payload["rows"] == 12
    finally:
        module.legacy_generate_csv = original


def test_runtime_export_does_not_execute_sync_helper_on_event_loop_thread():
    """The synchronous generator should not run directly on the event-loop thread."""
    module = load_app_module()
    client = TestClient(module.app)

    original = module.legacy_generate_csv
    marker = {"called": 0, "ran_inside_loop": False}

    def loop_probe(rows: int = 1200) -> str:
        marker["called"] += 1
        try:
            asyncio.get_running_loop()
            marker["ran_inside_loop"] = True
        except RuntimeError:
            marker["ran_inside_loop"] = False
        time.sleep(0.15)
        return "id,user,message\n0,user-0,msg\n"

    module.legacy_generate_csv = loop_probe
    try:
        response = client.get("/bulk-export", params={"rows": 15})
        assert response.status_code == 200
        assert marker["called"] >= 1, "legacy_generate_csv must be used"
        assert not marker["ran_inside_loop"], (
            "legacy_generate_csv executed on the event-loop thread"
        )
    finally:
        module.legacy_generate_csv = original


def test_runtime_health_stays_responsive_during_heavy_export():
    """Health checks should still complete quickly while export work is in flight."""
    module = load_app_module()
    client = TestClient(module.app)

    results = {"export_status": None}

    def hit_export() -> None:
        response = client.get("/bulk-export", params={"rows": 5000})
        results["export_status"] = response.status_code

    worker = threading.Thread(target=hit_export)
    worker.start()
    time.sleep(0.03)

    latencies: list[float] = []
    for _ in range(8):
        start = time.perf_counter()
        response = client.get("/health")
        latencies.append(time.perf_counter() - start)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    worker.join(timeout=5)
    assert not worker.is_alive(), "Export request did not complete in time"
    assert results["export_status"] == 200, "Export request failed"
    assert min(latencies) < 0.2, "No fast health response observed during export"
