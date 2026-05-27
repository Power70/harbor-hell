Our FastAPI service has event-loop starvation: when `/bulk-export` is called, other requests stall and users see timeouts.

Create `/app/main.py` with a FastAPI app that fixes the concurrency bug.

Requirements:
1. Define a synchronous helper named `legacy_generate_csv` that simulates the legacy blocking CSV export work.
2. Keep `bulk_export` as an `async def` GET endpoint and keep the export feature.
3. Offload the blocking helper using either `starlette.concurrency.run_in_threadpool` or `asyncio.to_thread`.
4. Keep a working GET `/health` endpoint that returns `{"status": "ok"}`.
5. `/bulk-export` must return JSON metadata for the export using these exact keys: `filename`, `rows`, `bytes`, and `generated_at`.
6. Use this response schema:
	 ```json
	 {
		 "filename": "bulk-export.csv",
		 "rows": 2000,
		 "bytes": 12345,
		 "generated_at": "2026-05-27T00:00:00+00:00"
	 }
	 ```
7. Do not solve this by removing features, changing worker counts, or adding infrastructure.

Expected outcome:
- `/bulk-export` still returns JSON metadata.
- `/health` remains responsive while export work is running.

Only create the application code needed to fix the root cause nothing else.
