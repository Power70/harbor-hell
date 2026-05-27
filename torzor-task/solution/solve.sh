#!/bin/bash
# Do NOT use set -e or set -euo pipefail

mkdir -p /app

cat > /app/main.py <<'PY'
import csv
import hashlib
import io
import time
from collections import deque
from datetime import UTC, datetime
from threading import Lock

from fastapi import FastAPI
from fastapi import Query
from starlette.concurrency import run_in_threadpool

app = FastAPI()
app.state.export_history = deque(maxlen=5)
app.state.history_lock = Lock()


def legacy_generate_csv(rows: int = 2000) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["id", "user", "message"])
    for i in range(rows):
        writer.writerow([i, f"user-{i}", f"message-{i}"])
        if i % 250 == 0:
            time.sleep(0.002)

    time.sleep(0.35)
    return output.getvalue()


def build_export_metadata(rows: int, csv_data: str) -> dict[str, object]:
    payload = csv_data.encode("utf-8")
    return {
        "filename": "bulk-export.csv",
        "rows": rows,
        "bytes": len(payload),
        "checksum_sha256": hashlib.sha256(payload).hexdigest(),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def record_export(metadata: dict[str, object]) -> None:
    with app.state.history_lock:
        app.state.export_history.appendleft(dict(metadata))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/bulk-export")
async def bulk_export(rows: int = Query(default=1200, ge=10, le=5000)) -> dict[str, object]:
    csv_data = await run_in_threadpool(legacy_generate_csv, rows)
    metadata = build_export_metadata(rows, csv_data)
    record_export(metadata)
    return metadata


@app.get("/exports/recent")
async def recent_exports() -> list[dict[str, object]]:
    with app.state.history_lock:
        return [dict(item) for item in app.state.export_history]
PY
