#!/bin/bash
# Do NOT use set -e or set -euo pipefail

mkdir -p /app

cat > /app/main.py <<'PY'
import csv
import io
import time

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
async def bulk_export() -> dict[str, int]:
	csv_data = await run_in_threadpool(legacy_generate_csv)
	return {"rows": 2000, "bytes": len(csv_data)}
PY
