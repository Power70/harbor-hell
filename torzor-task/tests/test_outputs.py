"""Behavioral tests for fixing FastAPI event-loop starvation in bulk export."""

from __future__ import annotations

import ast
import importlib.util
import hashlib
from pathlib import Path

from fastapi.testclient import TestClient


APP_PATH = Path("/app/main.py")
EXPECTED_SHA256 = "03a2bc98910e5e642cb1b105eb555c92e3e7da4cf4d1cbbd2cf6e399d356c888"


def _load_app_module():
    """Load /app/main.py as a Python module for runtime behavior checks."""
    spec = importlib.util.spec_from_file_location("target_app", APP_PATH)
    assert spec and spec.loader, "Could not load module spec from /app/main.py"

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    """Return the SHA256 digest of a file so the solution cannot mutate it silently."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bulk_export_uses_thread_offloading(source: str) -> bool:
    """Return True when bulk_export offloads legacy_generate_csv via thread helpers."""
    tree = ast.parse(source)

    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "bulk_export":
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Await):
                    continue

                call = sub.value
                if not isinstance(call, ast.Call):
                    continue

                callee_name = None
                if isinstance(call.func, ast.Name):
                    callee_name = call.func.id
                elif isinstance(call.func, ast.Attribute):
                    callee_name = call.func.attr

                if callee_name not in {"run_in_threadpool", "to_thread"}:
                    continue

                first_arg = call.args[0] if call.args else None
                if isinstance(first_arg, ast.Name) and first_arg.id == "legacy_generate_csv":
                    return True

            return False

    return False


def test_app_file_exists_for_fix_target():
    """The target application file should exist after setup or solution."""
    assert APP_PATH.exists(), "Expected /app/main.py to exist"


def test_app_file_has_expected_hash():
    """The fixed application must match the exact reviewed implementation."""
    assert _sha256(APP_PATH) == EXPECTED_SHA256, (
        "Unexpected /app/main.py hash; the fix must use the reviewed solution code"
    )


def test_health_endpoint_returns_expected_payload():
    """Health endpoint should stay available and return the expected payload."""
    module = _load_app_module()
    client = TestClient(module.app)

    response = client.get("/health")
    assert response.status_code == 200, "Expected /health to return HTTP 200"
    assert response.json() == {"status": "ok"}, "Unexpected /health payload"


def test_bulk_export_endpoint_still_present_and_returns_metadata():
    """Export feature must remain enabled and return useful metadata."""
    module = _load_app_module()
    client = TestClient(module.app)

    response = client.get("/bulk-export")
    assert response.status_code == 200, "Expected /bulk-export to return HTTP 200"

    payload = response.json()
    assert "rows" in payload and "bytes" in payload, (
        "Bulk export response must include rows and bytes"
    )
    assert payload["rows"] > 0, "rows should be positive"
    assert payload["bytes"] > 0, "bytes should be positive"


def test_bulk_export_offloads_blocking_work_from_event_loop():
    """bulk_export must offload legacy sync work with run_in_threadpool or to_thread."""
    source = APP_PATH.read_text()

    assert _bulk_export_uses_thread_offloading(source), (
        "bulk_export must await run_in_threadpool(legacy_generate_csv) or "
        "await asyncio.to_thread(legacy_generate_csv)"
    )
