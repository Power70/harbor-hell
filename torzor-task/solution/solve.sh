#!/bin/bash
# Do NOT use set -e or set -euo pipefail

mkdir -p /app

cat > /app/main.py <<'PY'
import csv
import hashlib
import io
import time
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi import Query
from starlette.concurrency import run_in_threadpool

app = FastAPI()


def legacy_generate_csv(rows: int = 2000) -> str:
	output = io.StringIO()
	writer = csv.writer(output)

	writer.writerow(["id", "user", "message"])
	for i in range(rows):
		writer.writerow([i, f"user-{i}", f"message-{i}"])
		if i % 250 == 0:
			time.sleep(0.002)

	time.sleep(0.45)
	return output.getvalue()


@app.get("/health")
async def health() -> dict[str, str]:
	return {"status": "ok"}


@app.get("/bulk-export")
async def bulk_export(rows: int = Query(default=1200, ge=10, le=5000)) -> dict[str, object]:
	csv_data = await run_in_threadpool(legacy_generate_csv, rows)
	payload_bytes = csv_data.encode("utf-8")
	return {
		"filename": "bulk-export.csv",
		"rows": rows,
		"bytes": len(payload_bytes),
		"checksum_sha256": hashlib.sha256(payload_bytes).hexdigest(),
		"generated_at": datetime.now(UTC).isoformat(),
	}
PY
