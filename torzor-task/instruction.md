Our FastAPI service has event-loop starvation: when `/bulk-export` is called, all other requests stall and users see timeouts.

Fix the concurrency bug in `/app/main.py`.

Requirements:
1. Keep `bulk_export` as an `async def` endpoint and keep the export feature.
2. The blocking legacy CSV generator must not run directly on the event loop.
3. Offload the blocking call using either `starlette.concurrency.run_in_threadpool` or `asyncio.to_thread`.
4. Keep a working `/health` endpoint that returns `{"status": "ok"}`.
5. Do not solve this by removing features, changing worker counts, or adding infrastructure.

Expected outcome:
- `/bulk-export` still returns a JSON payload with export metadata.
- `/health` remains responsive while export work is running.

Only modify application code needed to fix the root cause.
