"""Behavioral tests for fixing FastAPI event-loop starvation in bulk export."""

from __future__ import annotations

import ast
import importlib.util
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


def bulk_export_uses_thread_offloading(source: str) -> bool:
    """Return True when bulk_export offloads legacy_generate_csv via thread helpers."""
    tree = ast.parse(source)

    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "bulk_export":
            for sub_node in ast.walk(node):
                if not isinstance(sub_node, ast.Await):
                    continue

                call_expr = sub_node.value
                if not isinstance(call_expr, ast.Call):
                    continue

                callee_name = None
                if isinstance(call_expr.func, ast.Name):
                    callee_name = call_expr.func.id
                elif isinstance(call_expr.func, ast.Attribute):
                    callee_name = call_expr.func.attr

                if callee_name not in {"run_in_threadpool", "to_thread"}:
                    continue

                first_arg = call_expr.args[0] if call_expr.args else None
                if (
                    isinstance(first_arg, ast.Name)
                    and first_arg.id == "legacy_generate_csv"
                ):
                    return True

            return False

    return False


def test_app_file_exists_for_fix_target():
    """The target application file should exist after setup or solution."""
    assert APP_FILE_PATH.exists(), "Expected /app/main.py to exist"


def test_health_endpoint_returns_expected_payload():
    """Health endpoint should stay available and return the expected payload."""
    module = load_app_module()
    client = TestClient(module.app)

    response = client.get("/health")
    assert response.status_code == 200, "Expected /health to return HTTP 200"
    assert response.json() == {"status": "ok"}, "Unexpected /health payload"


def test_bulk_export_endpoint_still_present_and_returns_metadata():
    """Export feature must remain enabled and return useful metadata."""
    module = load_app_module()
    client = TestClient(module.app)

    response = client.get("/bulk-export")
    assert response.status_code == 200, "Expected /bulk-export to return HTTP 200"

    payload = response.json()
    assert "filename" in payload and "rows" in payload and "bytes" in payload, (
        "Bulk export response must include filename, rows, and bytes"
    )
    assert payload["rows"] > 0, "rows should be positive"
    assert payload["bytes"] > 0, "bytes should be positive"
    assert payload["filename"].endswith(".csv"), "filename should be a CSV file"


def test_bulk_export_offloads_blocking_work_from_event_loop():
    """bulk_export must offload legacy sync work with run_in_threadpool or to_thread."""
    source = APP_FILE_PATH.read_text()

    assert bulk_export_uses_thread_offloading(source), (
        "bulk_export must await run_in_threadpool(legacy_generate_csv) or "
        "await asyncio.to_thread(legacy_generate_csv)"
    )
