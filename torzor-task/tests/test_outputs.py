"""Behavioral tests for a responsive export service with recent history."""

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
    """Load /app/main.py as a Python module for runtime checks."""
    module_spec = importlib.util.spec_from_file_location("target_app", APP_FILE_PATH)
    assert module_spec and module_spec.loader, (
        "Could not load module spec from /app/main.py"
    )

    app_module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(app_module)
    return app_module


def test_file_exists():
    """The application file should be present."""
    assert APP_FILE_PATH.exists(), "Expected /app/main.py to exist"


def test_health_contract():
    """The status endpoint should remain available and exact."""
    module = load_app_module()
    client = TestClient(module.app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_export_contract():
    """The export endpoint should return the required metadata fields."""
    module = load_app_module()
    client = TestClient(module.app)

    response = client.get("/bulk-export")
    assert response.status_code == 200

    payload = response.json()
    assert set(payload) == {
        "filename",
        "rows",
        "bytes",
        "checksum_sha256",
        "generated_at",
    }
    assert payload["filename"] == "bulk-export.csv"
    assert payload["rows"] == 1200
    assert isinstance(payload["bytes"], int) and payload["bytes"] > 0
    assert isinstance(payload["checksum_sha256"], str)
    assert len(payload["checksum_sha256"]) == 64

    parsed = datetime.fromisoformat(payload["generated_at"])
    assert parsed.tzinfo is not None
    assert payload["generated_at"].endswith("+00:00")


def test_recent_history_starts_empty():
    """Recent history should be empty before any export runs."""
    module = load_app_module()
    client = TestClient(module.app)

    response = client.get("/exports/recent")
    assert response.status_code == 200
    assert response.json() == []


def test_export_validation():
    """Allowed export sizes should pass and out-of-range values should fail."""
    module = load_app_module()
    client = TestClient(module.app)

    assert client.get("/bulk-export", params={"rows": 10}).status_code == 200
    assert client.get("/bulk-export", params={"rows": 5000}).status_code == 200
    assert client.get("/bulk-export", params={"rows": 9}).status_code == 422
    assert client.get("/bulk-export", params={"rows": 5001}).status_code == 422


def test_export_checksum_matches_payload():
    """Checksum and byte count should match the actual generated CSV bytes."""
    module = load_app_module()
    client = TestClient(module.app)

    original = module.legacy_generate_csv
    csv_text = "id,user,message\n1,user-1,hello\n2,user-2,world\n"

    def fixed_csv(rows: int = 1200) -> str:
        return csv_text

    module.legacy_generate_csv = fixed_csv
    try:
        response = client.get("/bulk-export", params={"rows": 12})
        assert response.status_code == 200
        payload = response.json()
        expected_bytes = csv_text.encode("utf-8")
        assert payload["rows"] == 12
        assert payload["bytes"] == len(expected_bytes)
        assert payload["checksum_sha256"] == hashlib.sha256(expected_bytes).hexdigest()
    finally:
        module.legacy_generate_csv = original


def test_export_handles_unicode_payloads():
    """UTF-8 accounting should stay correct for non-ASCII CSV data."""
    module = load_app_module()
    client = TestClient(module.app)

    original = module.legacy_generate_csv
    csv_text = "id,user,message\n1,用户,naïve café\n2,данные,你好\n"

    def unicode_csv(rows: int = 1200) -> str:
        return csv_text

    module.legacy_generate_csv = unicode_csv
    try:
        response = client.get("/bulk-export", params={"rows": 24})
        assert response.status_code == 200
        payload = response.json()
        expected_bytes = csv_text.encode("utf-8")
        assert payload["bytes"] == len(expected_bytes)
        assert payload["checksum_sha256"] == hashlib.sha256(expected_bytes).hexdigest()
    finally:
        module.legacy_generate_csv = original


def test_recent_history_tracks_order_and_limit():
    """Recent export history should stay newest-first and capped."""
    module = load_app_module()
    client = TestClient(module.app)

    original = module.legacy_generate_csv

    def fixed_csv(rows: int = 1200) -> str:
        return f"id,user,message\n{rows},user-{rows},message-{rows}\n"

    module.legacy_generate_csv = fixed_csv
    try:
        for rows in [10, 11, 12, 13, 14, 15]:
            response = client.get("/bulk-export", params={"rows": rows})
            assert response.status_code == 200

        history = client.get("/exports/recent")
        assert history.status_code == 200
        entries = history.json()
        assert isinstance(entries, list)
        assert len(entries) == 5
        assert [entry["rows"] for entry in entries] == [15, 14, 13, 12, 11]
        assert all(entry["filename"] == "bulk-export.csv" for entry in entries)
    finally:
        module.legacy_generate_csv = original


def test_recent_history_survives_interleaved_health_checks():
    """Status requests should not disturb export history updates."""
    module = load_app_module()
    client = TestClient(module.app)

    original = module.legacy_generate_csv

    def fixed_csv(rows: int = 1200) -> str:
        return f"id,user,message\n{rows},user-{rows},message-{rows}\n"

    module.legacy_generate_csv = fixed_csv
    try:
        for rows in [31, 32, 33]:
            assert client.get("/health").status_code == 200
            assert client.get("/bulk-export", params={"rows": rows}).status_code == 200
            assert client.get("/health").status_code == 200

        entries = client.get("/exports/recent").json()
        assert [entry["rows"] for entry in entries[:3]] == [33, 32, 31]
    finally:
        module.legacy_generate_csv = original


def test_recent_history_reflects_latest_export():
    """The history endpoint should expose the latest export summary."""
    module = load_app_module()
    client = TestClient(module.app)

    original = module.legacy_generate_csv
    csv_text = "id,user,message\n17,user-17,seventeen\n"

    def fixed_csv(rows: int = 1200) -> str:
        return csv_text

    module.legacy_generate_csv = fixed_csv
    try:
        response = client.get("/bulk-export", params={"rows": 17})
        assert response.status_code == 200
        payload = response.json()

        history = client.get("/exports/recent")
        assert history.status_code == 200
        entries = history.json()
        assert entries[0]["rows"] == 17
        assert entries[0]["bytes"] == payload["bytes"]
        assert entries[0]["checksum_sha256"] == payload["checksum_sha256"]
    finally:
        module.legacy_generate_csv = original


def test_recent_history_keeps_latest_five_after_more_exports():
    """Only the five most recent exports should remain available."""
    module = load_app_module()
    client = TestClient(module.app)

    original = module.legacy_generate_csv

    def fixed_csv(rows: int = 1200) -> str:
        return f"id,user,message\n{rows},user-{rows},message-{rows}\n"

    module.legacy_generate_csv = fixed_csv
    try:
        for rows in [41, 42, 43, 44, 45, 46, 47]:
            assert client.get("/bulk-export", params={"rows": rows}).status_code == 200

        entries = client.get("/exports/recent").json()
        assert len(entries) == 5
        assert [entry["rows"] for entry in entries] == [47, 46, 45, 44, 43]
    finally:
        module.legacy_generate_csv = original


def test_export_helper_runs_off_the_loop_thread():
    """The synchronous generator should not execute on the event-loop thread."""
    module = load_app_module()
    client = TestClient(module.app)

    original = module.legacy_generate_csv
    marker = {"called": 0, "ran_in_loop": False}

    def probe(rows: int = 1200) -> str:
        marker["called"] += 1
        try:
            asyncio.get_running_loop()
            marker["ran_in_loop"] = True
        except RuntimeError:
            marker["ran_in_loop"] = False
        time.sleep(0.1)
        return "id,user,message\n0,user-0,msg\n"

    module.legacy_generate_csv = probe
    try:
        response = client.get("/bulk-export", params={"rows": 21})
        assert response.status_code == 200
        assert marker["called"] >= 1
        assert not marker["ran_in_loop"]
    finally:
        module.legacy_generate_csv = original


def test_health_stays_responsive_while_export_is_running():
    """Health checks should stay fast while a large export is in progress."""
    module = load_app_module()
    client = TestClient(module.app)

    original = module.legacy_generate_csv

    def slow_csv(rows: int = 1200) -> str:
        time.sleep(0.25)
        return "id,user,message\n0,user-0,msg\n"

    module.legacy_generate_csv = slow_csv
    try:
        result = {"status": None}

        def run_export() -> None:
            result["status"] = client.get(
                "/bulk-export", params={"rows": 5000}
            ).status_code

        worker = threading.Thread(target=run_export)
        worker.start()
        time.sleep(0.03)

        latencies: list[float] = []
        for _ in range(6):
            start = time.perf_counter()
            response = client.get("/health")
            latencies.append(time.perf_counter() - start)
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

        worker.join(timeout=5)
        assert not worker.is_alive()
        assert result["status"] == 200
        assert min(latencies) < 0.2
    finally:
        module.legacy_generate_csv = original


def test_concurrent_exports_record_all_latest_values():
    """Concurrent export requests should still leave a coherent recent-history snapshot."""
    module = load_app_module()
    client = TestClient(module.app)

    original = module.legacy_generate_csv

    def numbered_csv(rows: int = 1200) -> str:
        time.sleep(0.04 if rows % 2 == 0 else 0.01)
        return f"id,user,message\n{rows},user-{rows},message-{rows}\n"

    module.legacy_generate_csv = numbered_csv
    try:
        observed_statuses: list[int] = []

        def run_export(rows: int) -> None:
            observed_statuses.append(
                client.get("/bulk-export", params={"rows": rows}).status_code
            )

        worker_a = threading.Thread(target=run_export, args=(61,))
        worker_b = threading.Thread(target=run_export, args=(62,))
        worker_a.start()
        worker_b.start()
        worker_a.join(timeout=5)
        worker_b.join(timeout=5)

        assert observed_statuses == [200, 200]
        entries = client.get("/exports/recent").json()
        rows_seen = {entry["rows"] for entry in entries}
        assert {61, 62}.issubset(rows_seen)
    finally:
        module.legacy_generate_csv = original
