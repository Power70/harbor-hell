Implement `/app/main.py` as a FastAPI service for a legacy CSV export path that currently harms responsiveness.

Behavior requirements:
1. Provide `GET /health` returning exactly `{"status": "ok"}`.
2. Provide `GET /bulk-export` as an async endpoint with query param `rows` (default `1200`, valid range `10..5000`).
3. Keep a synchronous helper named `legacy_generate_csv(rows: int) -> str` that does the actual CSV generation work.
4. Export response must be JSON with exactly these keys:
   - `filename`
   - `rows`
   - `bytes`
   - `checksum_sha256`
   - `generated_at`
5. `filename` must be `bulk-export.csv`; `rows` must reflect the effective row count; `bytes` must be UTF-8 byte size of generated CSV content; `checksum_sha256` must match generated CSV bytes.
6. `generated_at` must be an ISO-8601 UTC timestamp including timezone offset.
7. During a heavy export call, the health endpoint must remain responsive.

Constraints:
- Preserve the export feature (no stubbing it out).
- Do not add external services, queues, or extra infrastructure.
- Keep implementation focused on this file only.
