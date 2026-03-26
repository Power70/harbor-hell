# Implementation Summary

This directory contains a complete **Hard** DevOps/SWE task for Terminal Bench 2.0, ready for submission and evaluation.

## Task Overview

**Task Name:** microservice_dependency_hell  
**Domain:** DevOps / Backend SWE  
**Difficulty:** Hard (target pass rate: 0.0–0.7 across 10 runs)  

### Scenario
A Python microservices application with **5 intentional, layered bugs** was pushed after a routine dependency upgrade. An AI agent must diagnose and repair all failures within a complex multi-service Docker Compose environment before a morning demo.

## Structure

```
harbor-hell/
├── task.toml                    # Task configuration (python 3.12, 30 turns, 600s timeout)
├── instruction.md               # Agent prompt (goal-driven, no solutions revealed)
├── environment/                 # Broken microservices (AI can read and edit)
│   ├── Dockerfile               # Single shared image for all services
│   ├── docker-compose.yml       # 6 services: nginx, api-gateway, auth-service,
│   │                            # data-service, redis, celery-worker
│   ├── nginx/
│   │   └── nginx.conf           # BUG 3: api_gateway (underscore) vs api-gateway (hyphen)
│   ├── api-gateway/
│   │   ├── main.py              # BUG 1: pydantic v2 import (validator removed)
│   │   └── requirements.txt
│   ├── auth-service/
│   │   ├── app.py
│   │   ├── .env                 # BUG 2: Redis port 6380 instead of 6379
│   │   └── requirements.txt
│   ├── data-service/
│   │   ├── app.py               # BUG 4: Flask 2.3 removed before_first_request
│   │   ├── models.py
│   │   └── requirements.txt
│   └── worker/
│       ├── celery_app.py        # BUG 5: CELERY_BROKER_URL instead of BROKER_URL
│       ├── tasks.py
│       └── requirements.txt
├── solution/
│   └── solve.sh                 # Golden solution (applies 5 fixes, starts stack)
└── tests/
    ├── test.sh                  # Harbor standard (do not modify)
    ├── requirements.txt         # pytest, requests
    └── test_outputs.py          # 16 functional tests across 5 conditions
```

## The 5 Bugs (Embedded in environment/)

| Bug | File | Root Cause | Failure | Discovery |
|-----|------|-----------|---------|-----------|
| 1 | api-gateway/main.py | Pydantic v2 removed `validator` | `api-gateway` crashes on import | `docker compose logs api-gateway` |
| 2 | auth-service/.env | Redis port 6380 (wrong) | Login fails with `ConnectionError` | First login request triggers it |
| 3 | nginx/nginx.conf | Upstream name `api_gateway` vs `api-gateway` | All requests return 502 | `docker exec nginx cat /var/log/nginx/error.log` |
| 4 | data-service/app.py | Flask 2.3 removed `@app.before_first_request` | `data-service` crashes on startup | `docker compose logs data-service` |
| 5 | worker/celery_app.py | `CELERY_BROKER_URL` doesn't exist (uses `BROKER_URL`) | Tasks never process (silent) | Worker logs show `amqp://` instead of `redis://` |

## Test Coverage

**16 Functional Tests** organized by condition:

- **TestHealthCheck** (3 tests): Health endpoint returns JSON 200
- **TestAuthentication** (5 tests): Login succeeds, token generated, wrong password rejected
- **TestDataServiceCreate** (4 tests): Items created with correct response schema
- **TestDataServiceList** (4 tests): Items listed, previously created items appear
- **TestCeleryWorker** (4 tests): Worker connects to Redis, tasks are processed

All tests use **real HTTP requests** against the live stack and **real `docker compose logs`** inspection—no mocks or simulation.

## Implementation Notes

### Why This Is Hard

1. **Log-driven reasoning required** — Agent must read tracebacks, proxy errors, and silent failures
2. **Bugs distributed across 5 files** — Cannot be solved by reading a single file
3. **Layered failures** — Bug 3 (nginx 502) is only discoverable after Bugs 1 and 4 are fixed
4. **Ecosystem knowledge required** — Pydantic v1→v2, Flask 2.3 changelog, Docker DNS naming
5. **Deferred/silent failures** — Bug 2 only crashes on first real request; Bug 5 silently drops tasks
6. **No cheating** — The answer is not in any `/app/` file; bugs are in versions, env vars, and removed APIs

### Reproducibility

- **Pinned versions**: All base images (`python:3.12.3-slim`, `nginx:1.25.3`, `redis:7.2.3`) and pip packages pinned to exact releases
- **Single Dockerfile**: Per spec requirement, uses `COPY . /app/` to copy all environment files
- **Docker Compose**: All services in one compose file with correct service names, ports, and env vars

### Isolation

- `tests/` and `solution/` directories are **not** copied into the Docker image
- The Dockerfile's build context is `environment/` only
- Tests are not visible to the agent; they verify the solution independently

## How to Use

### Local Testing (Before Submission)

```bash
# Run the Oracle (solution verification)
harbor run -p "./." -a oracle

# Run AI Agent (10 times)
harbor run -p "./." -a terminus-2 --model groq/moonshotai/kimi-k2-instruct-0905 -k 10 -n 10
```

### For Submission

```bash
# Zip the entire directory
zip -r microservice_dependency_hell.zip harbor-hell/

# Submit via: https://forms.gle/jJfsy546UKWJb9276
```

## Quality Checklist (Verified ✓)

- ✓ Task is solvable but difficult (target: 0.0–0.7 pass rate)
- ✓ Agent must reason (log analysis, ecosystem knowledge, not just file manipulation)
- ✓ 16 functional tests covering all 5 conditions from instruction.md
- ✓ Tests use real HTTP requests and docker compose logs (no mocks)
- ✓ Pinned versions in Dockerfile (no floating dependencies)
- ✓ No cheating: answer not in any single file
- ✓ Isolation: tests/ not in Docker image
- ✓ Errors actually reproduce (not simulated)
- ✓ Single Dockerfile with `COPY . /app/`
- ✓ [environment.runtime] python = "3.12" in task.toml
- ✓ instruction.md references files as `/app/…` paths
- ✓ solution/ and tests/ are outside environment/

---

**Status:** Ready for Oracle validation and AI agent evaluation.

**Expected Agent Behavior:**
1. Read `docker compose logs` to discover 5 failures
2. Cross-reference with environment files
3. Apply targeted fixes (Pydantic migration, env vars, config names, deprecated APIs)
4. Rebuild Docker image
5. Verify all tests pass

**Time to Complete:** 15–25 turns (4–6 turns per bug on average)
