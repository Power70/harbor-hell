#!/bin/bash
# Do NOT use set -e or set -euo pipefail

mkdir -p /app

cat > /app/main.py <<'PY'
import csv
import io
import time
from datetime import UTC, datetime

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

app = FastAPI()


def legacy_generate_csv(rows: int = 2000) -> str:
	output = io.StringIO()
	writer = csv.writer(output)

	for i in range(rows):
		writer.writerow([i, f"user-{i}", f"message-{i}"])
		if i % 300 == 0:
			time.sleep(0.005)

	time.sleep(0.8)
	return output.getvalue()


@app.get("/health")
async def health() -> dict[str, str]:
	return {"status": "ok"}


@app.get("/bulk-export")
async def bulk_export() -> dict[str, object]:
	csv_data = await run_in_threadpool(legacy_generate_csv)
	row_count = csv_data.count("\n") - 1
	return {
		"filename": "bulk-export.csv",
		"rows": row_count,
		"bytes": len(csv_data.encode("utf-8")),
		"generated_at": datetime.now(UTC).isoformat(),
	}
PY
