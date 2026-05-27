Implement `/app/main.py` as a FastAPI service that serves a legacy CSV export path without hurting responsiveness.

Behavior requirements:
1. `GET /health` returns exactly `{"status": "ok"}`.
2. `GET /bulk-export` is async, accepts `rows` (default `1200`, allowed range `10..5000`), and returns export metadata as JSON.
3. Keep the CSV generation synchronous inside the implementation, but do not let it block request handling.
4. Export metadata must include `filename`, `rows`, `bytes`, `checksum_sha256`, and `generated_at`.
5. `filename` is always `bulk-export.csv`; `rows` reflects the request; `bytes` and `checksum_sha256` must match the generated CSV payload; `generated_at` is an ISO-8601 UTC timestamp.
6. Keep a short in-memory history of the most recent export metadata and expose it from `GET /exports/recent` newest-first, capped to 5 entries.
7. Under export load, `GET /health` must still respond quickly.

Constraints:
- Preserve the export feature.
- Do not add external services, queues, or extra infrastructure.
- Keep the implementation in `/app/main.py`.
