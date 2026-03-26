# Terminal Bench 2.0 — Production-Ready Implementation Plan

**Task Name:** `microservice_dependency_hell`  
**Domain:** DevOps / Backend SWE  
**Target Difficulty:** Hard — expected AI agent pass rate **> 0.0 and < 0.7** across 10 runs  
**Originality:** Entirely original. No elements derived from any Harbor/Terminal Bench 1.0 or 2.0 registry.  
**Confidentiality:** This document must not be shared on any public forum.

---

## Gap Analysis vs. Spec (Read First)

Before the step-by-step plan, this section records every spec requirement and exactly how the plan satisfies it — so nothing is left unaddressed.

| Spec Requirement | Plan Response |
|-----------------|---------------|
| `harbor tasks init "name"` → creates `name@tasks.harborframework.com/` | Phase 1 uses `harbor tasks init "microservice_dependency_hell"` |
| `task.toml` must have `[environment.runtime] python = "3.12"` | Phase 2 includes this block verbatim |
| `instruction.md`: describe goal, not steps; reference files as `/app/file_name` | Phase 3 describes observable failure only; all paths are `/app/…` |
| `environment/Dockerfile`: **single** Dockerfile, **`COPY . /app/`** (spec says `COPY * /app/`; `.` is used instead of `*` to also copy hidden files like `.env`) | Phase 4 has ONE root `environment/Dockerfile` with `COPY . /app/` |
| All package installs in the one Dockerfile | The root Dockerfile installs all service requirements in a single `RUN pip install` chain |
| Do NOT include solution or test files in the image build or in environment/ | `solution/` and `tests/` live outside `environment/`; Dockerfile builds only from `environment/` context |
| `solution/solve.sh` invokes the fix scripts | Phase 5's `solve.sh` applies all 5 fixes then starts the stack |
| `tests/test_outputs.py` in pytest format | Phase 6 has 16 functional pytest test cases |
| `tests/test.sh` — do not touch | Included verbatim; marked as Harbor standard, do not modify |
| Harbor Oracle: `harbor run -p "./task@…" -a oracle` | Phase 7 shows exact command |
| AI agent run: `harbor run … -a terminus-2 --model groq/moonshotai/kimi-k2-instruct-0905 -k 10 -n 10` | Phase 8 shows exact command |
| Pass rate > 0.0 and < 0.7 | 5 layered bugs calibrated for Hard difficulty; section 13 gives tuning guidance |
| Agent must reason (logs, deps) not just manipulate files | All 5 bugs require log analysis and ecosystem knowledge |
| Multiple functional tests | 16 tests across 5 classes; all make real HTTP calls |
| Pinned versions | All pip packages and base images pin exact versions |
| No cheating by cat-ing files | Bugs are in version numbers, env vars, and removed API usage — no plaintext answer exists |
| tests/ not in Docker image | Docker build context is `environment/`; tests/ is a sibling directory |
| Errors actually reproduce | Wrong Redis port → real `ConnectionRefusedError`; wrong nginx upstream → real `502`; removed Flask API → real `AttributeError`; etc. |

---

## Table of Contents

1. [Design Philosophy & Task Concept](#1-design-philosophy--task-concept)
2. [Architecture Overview](#2-architecture-overview)
3. [Bug Inventory — Root Causes & Difficulty Analysis](#3-bug-inventory--root-causes--difficulty-analysis)
4. [Complete File & Folder Structure](#4-complete-file--folder-structure)
5. [Phase 1 — Local Environment Setup](#5-phase-1--local-environment-setup)
6. [Phase 2 — task.toml](#6-phase-2--tasktoml)
7. [Phase 3 — instruction.md](#7-phase-3--instructionmd)
8. [Phase 4 — environment/ (The Broken System)](#8-phase-4--environment-the-broken-system)
   - 8.1 [Dockerfile (Single Root — Spec Requirement)](#81-dockerfile-single-root--spec-requirement)
   - 8.2 [docker-compose.yml](#82-docker-composeyml)
   - 8.3 [nginx/nginx.conf](#83-nginxnginxconf)
   - 8.4 [api-gateway/](#84-api-gateway)
   - 8.5 [auth-service/](#85-auth-service)
   - 8.6 [data-service/](#86-data-service)
   - 8.7 [worker/](#87-worker)
9. [Phase 5 — solution/ (The Golden Fix)](#9-phase-5--solution-the-golden-fix)
10. [Phase 6 — tests/ (Verification Logic)](#10-phase-6--tests-verification-logic)
11. [Phase 7 — Oracle Validation](#11-phase-7--oracle-validation)
12. [Phase 8 — AI Agent Run](#12-phase-8--ai-agent-run)
13. [Difficulty Calibration & Tuning](#13-difficulty-calibration--tuning)
14. [Quality Checklist Sign-Off](#14-quality-checklist-sign-off)
15. [Submission Steps](#15-submission-steps)
16. [Appendix A — Exact Error Messages Per Bug](#appendix-a--exact-error-messages-per-bug)
17. [Appendix B — Manual Quick-Test Script](#appendix-b--manual-quick-test-script)

---

## 1. Design Philosophy & Task Concept

### Scenario

A Python microservices application running in Docker Compose "was working perfectly in staging." A junior engineer performed a routine dependency upgrade and pushed to main. Since that push, the entire stack is broken. The on-call senior DevOps engineer (the AI agent) must diagnose and repair all failures before a morning demo.

### Why This Is the Right "Hard" Task

| Property | How This Task Delivers It |
|----------|--------------------------|
| **Log-driven reasoning required** | Services crash with tracebacks, proxy errors, and silent failures — the agent must read and interpret them |
| **Cannot be solved by `cat`-ing one file** | Bugs are distributed across 5 separate files in 4 different technical layers |
| **Multi-step layered failures** | Bug 3 (nginx 502) cannot be discovered until Bugs 1 and 4 are fixed and the gateway starts |
| **Ecosystem knowledge required** | Bug 1 requires Pydantic v1→v2 migration knowledge; Bug 4 requires Flask 2.3 changelog knowledge |
| **Deferred / silent failures** | Bug 2 (Redis port) only manifests on the first real request, not at startup |
| **Reproducible** | All base images and package versions are pinned to exact releases |
| **No cheating** | No file in `/app/` contains the answer — bugs are in dependency versions, env vars, and removed API usage |

### Design Principle: Layered "Onion" Bugs

Each layer's fix reveals the next problem:

```
Layer 1 — api-gateway fails to start      (Bug 1: pydantic v2 import error)
Layer 2 — data-service fails to start     (Bug 4: Flask 2.3 removed API)
Layer 3 — nginx returns 502               (Bug 3: upstream DNS name mismatch)
Layer 4 — login request silently fails    (Bug 2: Redis wrong port)
Layer 5 — Celery tasks never processed    (Bug 5: wrong env var name)
```

---

## 2. Architecture Overview

```
  External Client
       │
       │  HTTP :8080
       ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                    Docker Compose Network                     │
  │                                                              │
  │  [nginx:1.25.3]  ── proxy_pass ──▶  [api-gateway:8000]     │
  │                                              │               │
  │                              ┌───────────────┴──────────┐   │
  │                              │                          │   │
  │                              ▼                          ▼   │
  │                   [auth-service:5001]       [data-service:5002] │
  │                              │                          │   │
  │                              └─────────┬────────────────┘   │
  │                                        ▼                    │
  │                                  [redis:7.2.3]              │
  │                                        │                    │
  │                                        ▼                    │
  │                               [celery-worker]               │
  └──────────────────────────────────────────────────────────────┘

  All Python services (api-gateway, auth-service, data-service,
  celery-worker) share ONE Docker image built from environment/Dockerfile.
  Each service overrides CMD and sets its own PYTHONPATH.
```

### Single-Image Architecture — Why and How

The spec explicitly requires **one `Dockerfile`** with `COPY * /app/` (equivalently `COPY . /app/`). This means:

1. One `environment/Dockerfile` installs all Python packages from all services' `requirements.txt` files into a single shared image.
2. `docker-compose.yml` uses `build: .` for every Python service — they all build from the same image.
3. Each service runs a different `command:` (e.g., `uvicorn main:app`, `flask run`, `celery worker`).
4. Each service sets `PYTHONPATH` to its own subdirectory inside `/app/` so Python can find its modules.

This is both spec-compliant AND realistic (a monorepo image pattern common in small microservices setups).

### PYTHONPATH Routing

| Service | PYTHONPATH | Entry Point |
|---------|-----------|-------------|
| `api-gateway` | `/app/api-gateway` | `uvicorn main:app` |
| `auth-service` | `/app/auth-service` | `flask --app app run` |
| `data-service` | `/app/data-service` | `flask --app app run` |
| `celery-worker` | `/app/worker` | `celery -A celery_app worker` |

---

## 3. Bug Inventory — Root Causes & Difficulty Analysis

### Bug 1 — Pydantic v2 Breaking Import in API Gateway

| Field | Value |
|-------|-------|
| **File** | `environment/api-gateway/main.py` |
| **Root Cause** | `from pydantic import validator` — `validator` was removed in Pydantic v2 (installed: `pydantic==2.3.0`) |
| **Failure Mode** | `api-gateway` crashes on startup: `ImportError: cannot import name 'validator' from 'pydantic'` |
| **Discovery** | `docker compose logs api-gateway` |
| **Fix** | Replace `validator` with `field_validator`; add `@classmethod`; update decorator syntax |
| **Why Hard** | Pydantic v2 migration is non-trivial. Downgrading to pydantic v1 breaks FastAPI 0.95.2. Only the code migration is correct. |

### Bug 2 — Redis Wrong Port in Auth Service Environment

| Field | Value |
|-------|-------|
| **File** | `environment/auth-service/.env` |
| **Root Cause** | `REDIS_URL=redis://redis:6380` — Redis listens on `6379` |
| **Failure Mode** | Service starts fine. First real `POST /auth/login` request → `redis.exceptions.ConnectionError: Error 111 connecting to redis:6380. Connection refused.` |
| **Discovery** | Send a login request, then `docker compose logs auth-service` |
| **Fix** | Change port `6380` → `6379` in `.env` |
| **Why Hard** | Service passes startup healthcheck. Agent may mark it "working" without actually testing login. |

### Bug 3 — Nginx Upstream Name Underscore vs. Hyphen

| Field | Value |
|-------|-------|
| **File** | `environment/nginx/nginx.conf` |
| **Root Cause** | `upstream api_gateway { server api_gateway:8000; }` — Docker DNS resolves service name `api-gateway` (hyphen), not `api_gateway` (underscore) |
| **Failure Mode** | All proxied requests return `502 Bad Gateway`. Nginx itself starts without error. |
| **Discovery** | `docker exec <nginx-container> cat /var/log/nginx/error.log` → `host not found in upstream "api_gateway"` |
| **Fix** | Replace `api_gateway` → `api-gateway` everywhere in `nginx.conf` |
| **Why Hard** | No crash at nginx startup. The error is inside the container's log file, not in `docker compose logs nginx`. Requires knowing Docker's DNS naming convention. |

### Bug 4 — Flask 2.3 Removed `before_first_request`

| Field | Value |
|-------|-------|
| **File** | `environment/data-service/app.py` |
| **Root Cause** | `@app.before_first_request` was removed in Flask 2.3.0 (installed: `flask==2.3.3`). The decorator no longer exists on the Flask app object. |
| **Failure Mode** | `data-service` crashes on startup: `AttributeError: 'Flask' object has no attribute 'before_first_request'` |
| **Discovery** | `docker compose logs data-service` |
| **Fix** | Replace the decorated function with `with app.app_context(): db.create_all()` at module level |
| **Why Hard** | Requires reading the Flask 2.3 changelog. The `AttributeError` message is on the app object, which the agent may attempt to fix by reinstalling Flask rather than migrating the code pattern. |

### Bug 5 — Celery Reads Wrong Environment Variable

| Field | Value |
|-------|-------|
| **File** | `environment/worker/celery_app.py` |
| **Root Cause** | `os.getenv("CELERY_BROKER_URL")` returns `None` because `docker-compose.yml` sets `BROKER_URL`, not `CELERY_BROKER_URL`. Celery falls back to `amqp://guest:guest@localhost//`. |
| **Failure Mode** | Worker starts and logs `celery@hostname ready.` — but is connected to a nonexistent AMQP broker. All enqueued tasks are never processed. |
| **Discovery** | Read worker logs: the "transport" line shows `amqp://` instead of `redis://`. Cross-reference with docker-compose.yml env block. |
| **Fix** | Change `os.getenv("CELERY_BROKER_URL")` to `os.getenv("BROKER_URL")` |
| **Why Hard** | Worker appears healthy. No crash. The only symptom is tasks never completing — which requires the agent to test the end-to-end flow, not just service startup. |

---

## 4. Complete File & Folder Structure

```
microservice_dependency_hell@tasks.harborframework.com/
│
├── task.toml
├── instruction.md
│
├── environment/                       ← Docker build context for ALL services
│   ├── Dockerfile                     ← SINGLE root Dockerfile (spec requirement)
│   ├── docker-compose.yml
│   ├── nginx/
│   │   └── nginx.conf                 ← BUG 3: upstream name mismatch
│   ├── api-gateway/
│   │   ├── main.py                    ← BUG 1: pydantic v2 import
│   │   └── requirements.txt
│   ├── auth-service/
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── .env                       ← BUG 2: Redis wrong port
│   ├── data-service/
│   │   ├── app.py                     ← BUG 4: Flask 2.3 removed API
│   │   ├── models.py
│   │   └── requirements.txt
│   └── worker/
│       ├── celery_app.py              ← BUG 5: wrong env var name
│       ├── tasks.py
│       └── requirements.txt
│
├── solution/
│   └── solve.sh                       ← applies all 5 fixes, then starts stack
│
└── tests/
    ├── test.sh                        ← Harbor standard — DO NOT MODIFY
    ├── requirements.txt               ← pytest + requests
    └── test_outputs.py                ← 16 functional tests
```

> **Key structural point:** There are NO per-service Dockerfiles. The single `environment/Dockerfile` is the ONLY Dockerfile. This strictly satisfies the spec's "Use the Dockerfile … add `COPY * /app/`" requirement.

> **Isolation proof:** `solution/` and `tests/` are siblings of `environment/`, not inside it. The Dockerfile's build context is `environment/`. These directories are never COPYd into any container.

---

## 5. Phase 1 — Local Environment Setup

Follow the spec's commands exactly:

```bash
# ── Install UV ──────────────────────────────────────────────────────────
curl -LsSf https://astral.sh/uv/install.sh | sh

# ── Create the Python environment ───────────────────────────────────────
uv init
uv venv --python 3.12
source .venv/bin/activate

# ── Install Harbor CLI ───────────────────────────────────────────────────
uv tool install harbor
harbor --version          # must print a version number

# ── Install Groq SDK ─────────────────────────────────────────────────────
uv pip install groq

# ── Store Groq API key (get from console.groq.com) ───────────────────────
touch .env
echo 'GROQ_API_KEY="your_groq_api_key"' > .env
export GROQ_API_KEY="your_groq_api_key"

# ── Verify Docker is running ─────────────────────────────────────────────
docker info               # must succeed

# ── Initialise the task skeleton ─────────────────────────────────────────
harbor tasks init "microservice_dependency_hell"
# Creates: microservice_dependency_hell@tasks.harborframework.com/

cd microservice_dependency_hell@tasks.harborframework.com

# ── Create all subdirectories ────────────────────────────────────────────
mkdir -p environment/nginx \
         environment/api-gateway \
         environment/auth-service \
         environment/data-service \
         environment/worker \
         solution \
         tests
```

---

## 6. Phase 2 — `task.toml`

**File:** `task.toml`

```toml
[task]
name        = "microservice_dependency_hell"
version     = "1.0.0"
description = "Diagnose and repair a broken Python microservices deployment with five layered dependency, configuration, and API-migration failures across FastAPI, Flask, Nginx, Redis, and Celery."
domain      = "devops"
difficulty  = "hard"
tags        = ["docker", "python", "microservices", "debugging", "dependency-management"]

[environment]
compose_file = "environment/docker-compose.yml"

[environment.runtime]
python = "3.12"

[agent]
max_turns = 30
timeout   = 600

[scoring]
pass_threshold = 1.0
```

**Why `timeout = 600`:** The agent must rebuild the Docker image (which re-runs pip install for all services) at least once, often twice. A cold pip install for all requirements takes ~60–90 seconds per build. Five debug-fix-rebuild cycles = ~5–10 minutes.

**Why `max_turns = 30`:** Each bug requires approximately 4–6 turns (read logs → identify → edit file → rebuild → verify). Five bugs × 5 turns = ~25 turns minimum. 30 gives a small buffer without making it trivially easy.

---

## 7. Phase 3 — `instruction.md`

**File:** `instruction.md`

```markdown
# Task: Repair the Broken Microservices Deployment

## Background

You are a senior DevOps engineer on call. A routine dependency upgrade was
pushed to the company's Python microservices application last night. Since that
push, **the entire stack is broken and the morning demo is in two hours**.

Your job is to diagnose every failure and restore the system to full operation.

## The System

All source code lives in `/app/`. The application is composed of:

| Component     | Technology               | Internal Address        |
|---------------|--------------------------|-------------------------|
| Reverse Proxy | nginx                    | `nginx:80` (→ `localhost:8080`) |
| API Gateway   | FastAPI                  | `api-gateway:8000`      |
| Auth Service  | Flask + Redis            | `auth-service:5001`     |
| Data Service  | Flask + SQLAlchemy       | `data-service:5002`     |
| Task Worker   | Celery + Redis           | —                       |
| Cache/Broker  | Redis                    | `redis:6379`            |

A `docker-compose.yml` is provided in `/app/`. All services are built from
the single `Dockerfile` in `/app/`.

## Definition of "Working"

The system is considered fully repaired when **all five** of the following
conditions hold simultaneously:

1. `GET http://localhost:8080/health`
   → HTTP 200, body: `{"status": "ok"}`

2. `POST http://localhost:8080/auth/login`
   Body: `{"username": "testuser", "password": "secret"}`
   → HTTP 200, body contains a `"token"` field (JWT string)

3. `POST http://localhost:8080/data/items`
   Header: `Authorization: Bearer <token>`
   Body: `{"name": "widget", "value": "blue"}`
   → HTTP 201, body contains `"id"`, `"name"`, `"value"` fields

4. `GET http://localhost:8080/data/items`
   Header: `Authorization: Bearer <token>`
   → HTTP 200, body is a JSON array; previously created items appear in it

5. `POST http://localhost:8080/data/notify`
   Header: `Authorization: Bearer <token>`
   Body: `{"message": "ping"}`
   → HTTP 200, AND the Celery worker processes the job (visible in worker
   logs as `"Task completed successfully: ping"`)

## Constraints

- You may read and edit any file under `/app/`.
- You may run `docker compose` commands from `/app/`.
- All fixes must be **persistent in files** — in-memory changes do not
  survive a container restart.
- Do not rename any service; do not change any exposed port.

## Suggested Starting Point

```bash
cd /app
docker compose up --build -d 2>&1 | tail -60
docker compose ps
docker compose logs --no-color 2>&1 | head -300
```

Analyse the output carefully. Not all failures are visible at startup.
```

---

## 8. Phase 4 — `environment/` (The Broken System)

> **No BUG comments appear in any of the files below.** All BUG annotations exist only in this implementation plan document. The environment files are clean source code that an agent must analyse through logs and inspection.

---

### 8.1 `Dockerfile` (Single Root — Spec Requirement)

**File:** `environment/Dockerfile`

This is the **single** Dockerfile for the entire environment, exactly as the spec requires. It:
- Uses a pinned base image
- Copies all files to `/app/` with `COPY . /app/`
- Installs all four services' Python requirements in one `RUN` layer
- Installs `curl` for healthcheck diagnostics

No service-level Dockerfiles exist anywhere in the project.

```dockerfile
FROM python:3.12.3-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       curl \
       libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all environment files into /app/ (equivalent to spec's COPY * /app/)
# Using COPY . /app/ instead of COPY * /app/ to also include hidden files (e.g. .env)
COPY . /app/

# Install all service dependencies in one shared Python environment
RUN pip install --upgrade pip==24.0 --no-cache-dir \
    && pip install --no-cache-dir -r /app/api-gateway/requirements.txt \
    && pip install --no-cache-dir -r /app/auth-service/requirements.txt \
    && pip install --no-cache-dir -r /app/data-service/requirements.txt \
    && pip install --no-cache-dir -r /app/worker/requirements.txt

EXPOSE 8000 5001 5002

CMD ["bash"]
```

---

### 8.2 `docker-compose.yml`

**File:** `environment/docker-compose.yml`

**Key design decisions:**
- All Python services use `build: .` — they all build from the single root Dockerfile above.
- Each Python service sets `PYTHONPATH` to its own subdirectory so Python's module resolver finds the service's source files.
- `BROKER_URL` (not `CELERY_BROKER_URL`) is set on the `celery-worker` service — this is part of Bug 5.
- `env_file: - ./auth-service/.env` causes Docker Compose to read the `.env` file (which contains Bug 2) from the host and inject it as environment variables into the container.
- No comments hint at any bug.

```yaml
version: "3.9"

services:

  nginx:
    image: nginx:1.25.3
    ports:
      - "8080:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - api-gateway
    restart: on-failure

  api-gateway:
    build: .
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app/api-gateway
      - AUTH_SERVICE_URL=http://auth-service:5001
      - DATA_SERVICE_URL=http://data-service:5002
    depends_on:
      - auth-service
      - data-service
    restart: on-failure

  auth-service:
    build: .
    command: flask --app app run --host 0.0.0.0 --port 5001
    ports:
      - "5001:5001"
    environment:
      - PYTHONPATH=/app/auth-service
    env_file:
      - ./auth-service/.env
    depends_on:
      - redis
    restart: on-failure

  data-service:
    build: .
    command: flask --app app run --host 0.0.0.0 --port 5002
    ports:
      - "5002:5002"
    environment:
      - PYTHONPATH=/app/data-service
      - DATABASE_URL=sqlite:////data/app.db
      - BROKER_URL=redis://redis:6379/0
    volumes:
      - data_volume:/data
    depends_on:
      - redis
    restart: on-failure

  redis:
    image: redis:7.2.3
    ports:
      - "6379:6379"
    restart: on-failure

  celery-worker:
    build: .
    command: celery -A celery_app worker --loglevel=info --concurrency=2
    environment:
      - PYTHONPATH=/app/worker
      - BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
      - data-service
    restart: on-failure

volumes:
  data_volume:
```

---

### 8.3 `nginx/nginx.conf`

**File:** `environment/nginx/nginx.conf`

**Bug 3 is here.** The upstream block uses `api_gateway` (underscore). The docker-compose service name is `api-gateway` (hyphen). Docker's embedded DNS resolves only the exact service name. `api_gateway` resolves to nothing, so every proxied request returns `502 Bad Gateway`. Nginx starts without any error at the container level.

```nginx
events {
    worker_connections 1024;
}

http {
    access_log /var/log/nginx/access.log;
    error_log  /var/log/nginx/error.log warn;

    upstream api_gateway {
        server api_gateway:8000;
    }

    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass         http://api_gateway;
            proxy_http_version 1.1;
            proxy_set_header   Host             $host;
            proxy_set_header   X-Real-IP        $remote_addr;
            proxy_set_header   X-Forwarded-For  $proxy_add_x_forwarded_for;
            proxy_read_timeout 30s;
        }
    }
}
```

---

### 8.4 `api-gateway/`

#### `environment/api-gateway/requirements.txt`

All packages are compatible at the pinned versions. The image builds successfully. The crash occurs at Python import time when the container starts.

```
fastapi==0.95.2
uvicorn[standard]==0.23.2
httpx==0.25.0
pydantic==2.3.0
python-jose[cryptography]==3.3.0
starlette==0.27.0
```

#### `environment/api-gateway/main.py`

**Bug 1 is here.** `from pydantic import validator` raises `ImportError` the moment Python loads this module because `validator` was removed in pydantic v2. The correct v2 replacement is `field_validator` (with `@classmethod`). The crash happens before the FastAPI application object is even created.

```python
import os
import httpx
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, validator

app = FastAPI(title="API Gateway", version="1.0.0")

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:5001")
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://data-service:5002")


class LoginRequest(BaseModel):
    username: str
    password: str

    @validator("username")
    def username_not_empty(cls, v):
        if not v.strip():
            raise ValueError("username must not be blank")
        return v.strip()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/auth/login")
async def login(req: LoginRequest):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{AUTH_SERVICE_URL}/login",
            json={"username": req.username, "password": req.password},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.json())
    return resp.json()


@app.post("/data/items", status_code=201)
async def create_item(
    payload: dict,
    authorization: str = Header(default=None),
):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{DATA_SERVICE_URL}/items",
            json=payload,
            headers={"Authorization": authorization or ""},
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@app.get("/data/items")
async def list_items(authorization: str = Header(default=None)):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{DATA_SERVICE_URL}/items",
            headers={"Authorization": authorization or ""},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@app.post("/data/notify")
async def notify(
    payload: dict,
    authorization: str = Header(default=None),
):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{DATA_SERVICE_URL}/notify",
            json=payload,
            headers={"Authorization": authorization or ""},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
```

---

### 8.5 `auth-service/`

#### `environment/auth-service/requirements.txt`

No bugs. All versions are compatible.

```
flask==2.3.3
flask-jwt-extended==4.5.3
redis==5.0.1
Werkzeug==2.3.7
```

#### `environment/auth-service/.env`

**Bug 2 is here.** Port `6380` is wrong. Redis listens on `6379`. Docker Compose reads this file on the host (via `env_file:`) and passes the variables into the container as environment variables. The auth-service starts cleanly because `redis-py` is lazy — it only attempts a connection when a command is issued. The `ConnectionRefusedError` fires on the first real login request when `redis_client.setex(...)` is called.

```
REDIS_URL=redis://redis:6380
JWT_SECRET_KEY=t3rminalb3nch-jwt-s3cr3t-k3y-2024
```

#### `environment/auth-service/app.py`

No bugs in this file. Logic is intentionally straightforward.

```python
import os
import redis as redis_client
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "fallback-secret")

jwt = JWTManager(app)

USERS = {
    "testuser": "secret",
    "admin":    "adminpass",
}

_redis = redis_client.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379"),
    decode_responses=True,
)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if not username or USERS.get(username) != password:
        return jsonify({"error": "Invalid credentials"}), 401

    # Fails at this line if REDIS_URL port is wrong
    _redis.setex(f"session:{username}", 3600, "active")

    token = create_access_token(identity=username)
    return jsonify({"token": token})


@app.route("/validate", methods=["POST"])
def validate():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")
    return jsonify({"valid": bool(token)})
```

---

### 8.6 `data-service/`

#### `environment/data-service/requirements.txt`

No bugs. All versions compatible.

```
flask==2.3.3
flask-sqlalchemy==3.1.1
SQLAlchemy==2.0.21
celery==5.3.4
redis==5.0.1
Werkzeug==2.3.7
```

#### `environment/data-service/models.py`

No bugs in this file.

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Item(db.Model):
    __tablename__ = "items"

    id    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name  = db.Column(db.String(200), nullable=False)
    value = db.Column(db.String(500), nullable=False, default="")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "value": self.value}
```

#### `environment/data-service/app.py`

**Bug 4 is here.** `@app.before_first_request` was removed in Flask 2.3.0. When Python loads this module, the decorator call immediately raises `AttributeError: 'Flask' object has no attribute 'before_first_request'`. The service crashes before it can accept any request.

```python
import os
from flask import Flask, request, jsonify
from models import db, Item
from celery import Celery

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:////data/app.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

broker_url = os.getenv("BROKER_URL", "redis://redis:6379/0")
celery_app = Celery(broker=broker_url)


@app.before_first_request
def initialise_database():
    db.create_all()


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/items", methods=["POST"])
def create_item():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    item = Item(name=data["name"], value=data.get("value", ""))
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@app.route("/items", methods=["GET"])
def list_items():
    items = Item.query.all()
    return jsonify([i.to_dict() for i in items])


@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "no-message")
    celery_app.send_task(
        "tasks.send_notification",
        args=[message],
        queue="celery",
    )
    return jsonify({"status": "enqueued", "message": message})
```

---

### 8.7 `worker/`

#### `environment/worker/requirements.txt`

No bugs.

```
celery==5.3.4
redis==5.0.1
```

#### `environment/worker/celery_app.py`

**Bug 5 is here.** `os.getenv("CELERY_BROKER_URL")` returns `None` because `docker-compose.yml` defines `BROKER_URL`. Celery's default fallback is `amqp://guest:guest@localhost//`. The worker starts and prints `celery@host ready.` — but it is connected to a nonexistent AMQP broker, not Redis. All tasks are silently dropped.

```python
import os
from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost//")

app = Celery(
    "worker",
    broker=broker_url,
    backend=broker_url,
    include=["tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
```

#### `environment/worker/tasks.py`

No bugs in this file.

```python
from celery_app import app


@app.task(name="tasks.send_notification", bind=True, max_retries=3)
def send_notification(self, message: str) -> dict:
    print(f"Task completed successfully: {message}", flush=True)
    return {"status": "done", "message": message}
```

---

## 9. Phase 5 — `solution/` (The Golden Fix)

**File:** `solution/solve.sh`

This is the only file in `solution/`. All 5 fixes are inlined to avoid path-resolution ambiguity with Harbor's mount points. The script:

1. Applies all 5 fixes using `sed` and Python heredocs (safer than regex for multi-line code changes).
2. Tears down any existing stack state (including volumes) for a clean rebuild.
3. Rebuilds and starts all services with `docker compose up --build -d`.
4. Polls `localhost:8080/health` in a loop (up to 120 seconds) — exits `0` only when the stack is confirmed healthy.

```bash
#!/usr/bin/env bash
# ============================================================
# solve.sh — Golden solution for microservice_dependency_hell
# ============================================================
set -euo pipefail

APP_DIR="/app"

echo "=================================================="
echo " Fix 1/5 — Pydantic v2: validator → field_validator"
echo "=================================================="
python3 - <<'PYEOF'
path = "/app/api-gateway/main.py"
src  = open(path).read()

# Fix import
src = src.replace(
    "from pydantic import BaseModel, validator",
    "from pydantic import BaseModel, field_validator",
)

# Fix decorator name
src = src.replace(
    '    @validator("username")',
    '    @field_validator("username")',
)

# Add required @classmethod for pydantic v2
old = '    @field_validator("username")\n    def username_not_empty(cls, v):'
new = '    @field_validator("username")\n    @classmethod\n    def username_not_empty(cls, v):'
src = src.replace(old, new)

open(path, "w").write(src)
print("  [OK] api-gateway/main.py patched — pydantic v2 field_validator")
PYEOF

echo ""
echo "=================================================="
echo " Fix 2/5 — Auth service: Redis port 6380 → 6379"
echo "=================================================="
ENV_FILE="$APP_DIR/auth-service/.env"
if grep -q "redis:6380" "$ENV_FILE"; then
    sed -i 's/redis:\/\/redis:6380/redis:\/\/redis:6379/g' "$ENV_FILE"
    echo "  [OK] auth-service/.env: REDIS_URL port corrected to 6379"
else
    echo "  [SKIP] Redis port already 6379"
fi

echo ""
echo "=================================================="
echo " Fix 3/5 — Nginx: upstream api_gateway → api-gateway"
echo "=================================================="
NGINX_CONF="$APP_DIR/nginx/nginx.conf"
if grep -q "api_gateway" "$NGINX_CONF"; then
    sed -i 's/api_gateway/api-gateway/g' "$NGINX_CONF"
    echo "  [OK] nginx/nginx.conf: upstream name corrected to api-gateway"
else
    echo "  [SKIP] Nginx upstream already uses api-gateway"
fi

echo ""
echo "=================================================="
echo " Fix 4/5 — Flask 2.3: remove before_first_request"
echo "=================================================="
python3 - <<'PYEOF'
path = "/app/data-service/app.py"
src  = open(path).read()

old_block = (
    "@app.before_first_request\n"
    "def initialise_database():\n"
    "    db.create_all()\n"
)
new_block = (
    "with app.app_context():\n"
    "    db.create_all()\n"
)

if old_block in src:
    src = src.replace(old_block, new_block)
    open(path, "w").write(src)
    print("  [OK] data-service/app.py: before_first_request → app_context")
else:
    print("  [SKIP] before_first_request not found (already fixed)")
PYEOF

echo ""
echo "=================================================="
echo " Fix 5/5 — Celery: CELERY_BROKER_URL → BROKER_URL"
echo "=================================================="
CELERY_APP="$APP_DIR/worker/celery_app.py"
if grep -q "CELERY_BROKER_URL" "$CELERY_APP"; then
    sed -i 's/CELERY_BROKER_URL/BROKER_URL/g' "$CELERY_APP"
    echo "  [OK] worker/celery_app.py: env var corrected to BROKER_URL"
else
    echo "  [SKIP] BROKER_URL already used"
fi

echo ""
echo "=================================================="
echo " Starting stack (rebuild required after file edits)"
echo "=================================================="
cd "$APP_DIR"

docker compose down --remove-orphans --volumes 2>/dev/null || true
docker compose up --build -d

echo ""
echo "  Waiting for stack (max 120s)..."
DEADLINE=$(( $(date +%s) + 120 ))
while true; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
             http://localhost:8080/health 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo "  [OK] HTTP 200 on /health — stack is healthy"
        break
    fi
    NOW=$(date +%s)
    if [ "$NOW" -ge "$DEADLINE" ]; then
        echo "  [ERROR] Stack not healthy after 120s (last HTTP: $STATUS)"
        docker compose logs --no-color --tail=80
        exit 1
    fi
    echo "  ... HTTP $STATUS — retrying in 5s ($(( DEADLINE - NOW ))s left)"
    sleep 5
done

echo ""
echo "=================================================="
echo " All 5 fixes applied. Stack is running."
echo "=================================================="
```

Make it executable:

```bash
chmod +x solution/solve.sh
```

---

## 10. Phase 6 — `tests/` (Verification Logic)

### `tests/requirements.txt`

```
pytest==7.4.3
requests==2.31.0
```

### `tests/test.sh`

> **Do not modify this file.** Harbor uses it to invoke pytest. Include it exactly as shown below.

```bash
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
pip install -r requirements.txt -q 2>/dev/null
pytest test_outputs.py -v --tb=short 2>&1
```

### `tests/test_outputs.py`

All 16 tests are **fully functional** — real HTTP requests against the live stack, real `docker compose logs` inspection. No mocks anywhere. Each test class corresponds to exactly one condition from `instruction.md`.

```python
"""
Functional test suite — microservice_dependency_hell
Maps directly to the 5 conditions in instruction.md.

Classes:
    TestHealthCheck        → Condition 1
    TestAuthentication     → Condition 2
    TestDataServiceCreate  → Condition 3
    TestDataServiceList    → Condition 4
    TestCeleryWorker       → Condition 5
"""

import subprocess
import time
import pytest
import requests

# ──────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────
BASE_URL      = "http://localhost:8080"
COMPOSE_DIR   = "/app"
TEST_CREDS    = {"username": "testuser", "password": "secret"}
WRONG_CREDS   = {"username": "testuser", "password": "wrongpassword"}
POLL_INTERVAL = 3.0   # seconds between readiness polls
POLL_MAX      = 40    # 40 × 3s = 120s max wait


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
def wait_for_stack(url: str = f"{BASE_URL}/health") -> None:
    """Block until stack returns HTTP 200, or fail with a helpful message."""
    for _ in range(POLL_MAX):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(POLL_INTERVAL)
    pytest.fail(
        f"Stack at {url} did not become reachable after "
        f"{POLL_MAX * POLL_INTERVAL:.0f}s.\n"
        "Run `docker compose ps` and `docker compose logs` to debug."
    )


def get_auth_token() -> str:
    """Obtain a valid JWT via the gateway login endpoint."""
    wait_for_stack()
    r = requests.post(f"{BASE_URL}/auth/login", json=TEST_CREDS, timeout=15)
    assert r.status_code == 200, (
        f"Login failed ({r.status_code}): {r.text}\n"
        "Check: nginx upstream name (Bug 3), auth-service Redis port (Bug 2)."
    )
    token = r.json().get("token")
    assert token, f"No 'token' in login response: {r.json()}"
    return token


def compose_logs(service: str) -> str:
    result = subprocess.run(
        ["docker", "compose", "logs", "--no-color", service],
        capture_output=True, text=True, cwd=COMPOSE_DIR,
    )
    return result.stdout + result.stderr


def compose_ps() -> str:
    result = subprocess.run(
        ["docker", "compose", "ps"],
        capture_output=True, text=True, cwd=COMPOSE_DIR,
    )
    return result.stdout


# ──────────────────────────────────────────────────────────
# Condition 1 — Health endpoint (3 tests)
# ──────────────────────────────────────────────────────────
class TestHealthCheck:

    def test_health_returns_http_200(self):
        wait_for_stack()
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        assert r.status_code == 200, (
            f"Expected HTTP 200, got {r.status_code}.\n"
            "If 502: nginx upstream name is still wrong (api_gateway vs api-gateway).\n"
            f"Body: {r.text}"
        )

    def test_health_body_equals_status_ok(self):
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        assert r.json() == {"status": "ok"}, (
            f"Unexpected body: {r.json()}"
        )

    def test_health_content_type_is_json(self):
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        ct = r.headers.get("content-type", "")
        assert "application/json" in ct, (
            f"Expected JSON content-type, got: {ct}"
        )


# ──────────────────────────────────────────────────────────
# Condition 2 — Authentication (5 tests)
# ──────────────────────────────────────────────────────────
class TestAuthentication:

    def test_valid_login_returns_http_200(self):
        wait_for_stack()
        r = requests.post(f"{BASE_URL}/auth/login", json=TEST_CREDS, timeout=15)
        assert r.status_code == 200, (
            f"Login returned {r.status_code}.\nBody: {r.text}\n"
            "If 500/502: check auth-service logs for Redis ConnectionError "
            "(wrong port in auth-service/.env)."
        )

    def test_login_response_contains_token_key(self):
        r = requests.post(f"{BASE_URL}/auth/login", json=TEST_CREDS, timeout=15)
        assert "token" in r.json(), (
            f"No 'token' key in response: {r.json()}"
        )

    def test_token_is_a_non_trivial_string(self):
        r = requests.post(f"{BASE_URL}/auth/login", json=TEST_CREDS, timeout=15)
        token = r.json().get("token", "")
        assert isinstance(token, str) and len(token) > 20, (
            f"Token looks invalid: {token!r}"
        )

    def test_wrong_password_returns_401(self):
        r = requests.post(f"{BASE_URL}/auth/login", json=WRONG_CREDS, timeout=15)
        assert r.status_code == 401, (
            f"Expected 401 for wrong password, got {r.status_code}."
        )

    def test_blank_credentials_return_4xx(self):
        r = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": "", "password": ""},
            timeout=15,
        )
        assert r.status_code in (400, 401, 422), (
            f"Expected 4xx for empty credentials, got {r.status_code}."
        )


# ──────────────────────────────────────────────────────────
# Condition 3 — Create item via data service (4 tests)
# ──────────────────────────────────────────────────────────
class TestDataServiceCreate:

    @pytest.fixture(scope="class")
    def token(self):
        return get_auth_token()

    def test_create_item_returns_http_201(self, token):
        r = requests.post(
            f"{BASE_URL}/data/items",
            json={"name": "probe-widget", "value": "blue"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert r.status_code == 201, (
            f"Expected 201, got {r.status_code}.\nBody: {r.text}\n"
            "If 502: api-gateway may still be crashing (pydantic v1 import).\n"
            "If 500: data-service may still be crashing "
            "(before_first_request removed in Flask 2.3)."
        )

    def test_create_item_response_has_id(self, token):
        r = requests.post(
            f"{BASE_URL}/data/items",
            json={"name": "id-check", "value": "green"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert "id" in r.json(), f"No 'id' in response: {r.json()}"

    def test_create_item_response_has_name(self, token):
        r = requests.post(
            f"{BASE_URL}/data/items",
            json={"name": "name-check", "value": "red"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert "name" in r.json(), f"No 'name' in response: {r.json()}"

    def test_create_item_id_is_integer(self, token):
        r = requests.post(
            f"{BASE_URL}/data/items",
            json={"name": "int-check", "value": "purple"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert isinstance(r.json().get("id"), int), (
            f"'id' should be int, got: {r.json().get('id')!r}"
        )


# ──────────────────────────────────────────────────────────
# Condition 4 — List items via data service (4 tests)
# ──────────────────────────────────────────────────────────
class TestDataServiceList:

    @pytest.fixture(scope="class")
    def token(self):
        return get_auth_token()

    def test_list_items_returns_http_200(self, token):
        r = requests.get(
            f"{BASE_URL}/data/items",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert r.status_code == 200, (
            f"Expected 200, got {r.status_code}.\nBody: {r.text}"
        )

    def test_list_items_returns_json_array(self, token):
        r = requests.get(
            f"{BASE_URL}/data/items",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert isinstance(r.json(), list), (
            f"Expected JSON array, got {type(r.json())}: {r.json()}"
        )

    def test_created_item_appears_in_list(self, token):
        """Create an item with a unique name, then verify it appears in GET."""
        unique_name = f"list-verify-{int(time.time())}"
        headers = {"Authorization": f"Bearer {token}"}
        post_r = requests.post(
            f"{BASE_URL}/data/items",
            json={"name": unique_name, "value": "list-test"},
            headers=headers, timeout=15,
        )
        assert post_r.status_code == 201, (
            f"Create failed before list check: {post_r.status_code} {post_r.text}"
        )
        get_r = requests.get(
            f"{BASE_URL}/data/items", headers=headers, timeout=15,
        )
        names = [item.get("name") for item in get_r.json()]
        assert unique_name in names, (
            f"Item '{unique_name}' not in list.\nFull list: {names}"
        )

    def test_list_items_each_entry_has_id_name_value(self, token):
        headers = {"Authorization": f"Bearer {token}"}
        requests.post(
            f"{BASE_URL}/data/items",
            json={"name": "schema-check", "value": "schema-val"},
            headers=headers, timeout=15,
        )
        r = requests.get(f"{BASE_URL}/data/items", headers=headers, timeout=15)
        items = r.json()
        assert len(items) > 0, "Item list is empty"
        for item in items:
            for field in ("id", "name", "value"):
                assert field in item, f"Item missing '{field}': {item}"


# ──────────────────────────────────────────────────────────
# Condition 5 — Celery background task (4 tests)
# ──────────────────────────────────────────────────────────
class TestCeleryWorker:

    @pytest.fixture(scope="class")
    def token(self):
        return get_auth_token()

    def test_worker_container_is_running(self):
        ps_out = compose_ps()
        assert "celery-worker" in ps_out, (
            f"celery-worker not found in docker compose ps:\n{ps_out}"
        )

    def test_worker_connected_to_redis_not_amqp(self):
        logs = compose_logs("celery-worker")
        assert "redis://" in logs, (
            "Worker logs do not show a Redis broker URL.\n"
            "The worker is connected to the AMQP default fallback — "
            "check CELERY_BROKER_URL vs BROKER_URL in worker/celery_app.py.\n"
            f"Worker logs:\n{logs[:3000]}"
        )

    def test_notify_endpoint_returns_200(self, token):
        r = requests.post(
            f"{BASE_URL}/data/notify",
            json={"message": "healthcheck-ping"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert r.status_code == 200, (
            f"Expected 200 from /data/notify, got {r.status_code}.\nBody: {r.text}"
        )

    def test_task_is_processed_by_worker(self, token):
        """
        Enqueue a uniquely-named task, wait 10s for processing,
        then verify the worker log contains the completion message.
        """
        unique_msg = f"tb2-task-{int(time.time())}"
        r = requests.post(
            f"{BASE_URL}/data/notify",
            json={"message": unique_msg},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert r.status_code == 200, f"Notify failed: {r.status_code} {r.text}"

        time.sleep(10)  # allow worker to pick up and process the task

        logs = compose_logs("celery-worker")
        expected = f"Task completed successfully: {unique_msg}"
        assert expected in logs, (
            f"Expected '{expected}' in worker logs — task was enqueued but "
            "not processed.\nCheck broker connection (Bug 5).\n"
            f"Worker logs (last 3000 chars):\n{logs[-3000:]}"
        )
```

---

## 11. Phase 7 — Oracle Validation

Run from the **parent directory** of the task folder:

```bash
harbor run -p "./microservice_dependency_hell@tasks.harborframework.com" -a oracle
```

The Oracle:
1. Mounts the task directory
2. Runs `solution/solve.sh`
3. Runs `pytest tests/test_outputs.py -v` via `tests/test.sh`

**Expected result:** All 16 tests pass. Exit code 0.

### Debugging Oracle Failures

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `solve.sh: docker: command not found` | Docker not in Harbor sandbox | See Harbor docs on Docker-in-Docker |
| `ModuleNotFoundError` on startup | PYTHONPATH not set or wrong | Confirm `environment` block in docker-compose.yml per service |
| `Health check timed out after 120s` | One service still crashing after fixes | Run `solve.sh` manually, then `docker compose logs` |
| `Login failed (500)` after solve | Bug 2 sed pattern didn't match | Check `.env` file content exactly matches the `sed` pattern |
| `Task completed` not in worker logs | Bug 5 not applied or timing | Increase `time.sleep(10)` in test; manually check worker logs |
| `ModuleNotFoundError: No module named 'models'` | PYTHONPATH for data-service missing | Confirm `PYTHONPATH=/app/data-service` in docker-compose.yml |

---

## 12. Phase 8 — AI Agent Run

Run from the **parent directory** of the task folder:

```bash
harbor run \
  -p "./microservice_dependency_hell@tasks.harborframework.com" \
  -a terminus-2 \
  --model groq/moonshotai/kimi-k2-instruct-0905 \
  -k 10 \
  -n 10
```

**Expected pass rate:** 0.15–0.55 (Hard range)  
**Expected avg turns:** 15–25  

Monitor the report for:
- `pass_rate` between `0.0` and `0.7`
- Individual run logs showing the agent reading `docker compose logs` and making targeted edits

---

## 13. Difficulty Calibration & Tuning

| Pass Rate | Interpretation | Action |
|-----------|---------------|--------|
| `0.0` | Too hard or environment bug | Reduce to 3 bugs; add `Start with docker compose logs` hint; raise `max_turns` to 40 |
| `0.1–0.3` | Hard end of target | Acceptable |
| `0.3–0.6` | Middle of target | Ideal |
| `0.6–0.7` | Easy end of target | Acceptable |
| `> 0.7` | Fails difficulty requirement | Add Bug 6 (below) or reduce `max_turns` to 20 |

### Optional Bug 6 (Hardener)

If pass rate exceeds 0.7, add this bug to `data-service/app.py`:

Replace `Item.query.all()` (Flask-SQLAlchemy legacy `LegacyQuery` API) with `db.engine.execute("SELECT * FROM items")` (removed in SQLAlchemy 2.0). This adds an `AttributeError` that surfaces only on `GET /data/items`. Fix: migrate to `db.session.execute(db.select(Item)).scalars().all()`.

---

## 14. Quality Checklist Sign-Off

| Spec Requirement | Status | Evidence |
|-----------------|--------|---------|
| Test suite covers everything in instruction.md | ✅ | 5 test classes mirror 5 conditions exactly |
| Tests do functional tests | ✅ | All 16 tests make real HTTP requests or inspect real container logs |
| Multiple functional tests | ✅ | 16 tests across 5 classes |
| Pinned versions in Dockerfile | ✅ | `python:3.12.3-slim`, `nginx:1.25.3`, `redis:7.2.3`; all pip packages pinned |
| No cheating by cat-ing files | ✅ | Bug 1: need to know pydantic v2 API. Bug 2: need to make a request to trigger it. Bug 3: need nginx internal logs. Bug 4: need Flask 2.3 changelog. Bug 5: need to cross-ref env var names. None readable from a single file. |
| tests/ not in Docker image | ✅ | Dockerfile builds from `environment/` context only; `tests/` and `solution/` are sibling directories |
| Errors actually reproduce | ✅ | Wrong Redis port → real `ConnectionRefusedError`. Wrong nginx upstream → real `502`. Flask removed API → real `AttributeError`. Wrong env var → Celery connects to nonexistent AMQP. |
| Single Dockerfile with `COPY . /app/` | ✅ | `environment/Dockerfile` is the ONLY Dockerfile. Uses `COPY . /app/`. No per-service Dockerfiles. |
| `[environment.runtime] python = "3.12"` in task.toml | ✅ | Included verbatim in Phase 2 |
| instruction.md references files as `/app/...` | ✅ | All file references in instruction.md use `/app/` prefix |
| Solution does not appear in environment/ | ✅ | `solution/` is outside `environment/`; no fix logic anywhere in `/app/` |

---

## 15. Submission Steps

```bash
# ── A. Final Oracle Verification ────────────────────────────────────────
harbor run -p "./microservice_dependency_hell@tasks.harborframework.com" -a oracle
# Expected: PASS — all 16 tests green

# ── B. AI Agent Run (k=10 required by spec) ─────────────────────────────
harbor run \
  -p "./microservice_dependency_hell@tasks.harborframework.com" \
  -a terminus-2 \
  --model groq/moonshotai/kimi-k2-instruct-0905 \
  -k 10 -n 10
# Expected: pass_rate in (0.0, 0.7) — save the report as evidence

# ── C. Confirm no bug hints in environment/ ──────────────────────────────
grep -r "BUG\|fix\|CELERY_BROKER_URL\|api_gateway\|6380\|before_first_request\|validator" \
     microservice_dependency_hell@tasks.harborframework.com/environment/ \
     --include="*.py" --include="*.conf" --include="*.env" \
     --include="*.yml" --include="*.toml" -l
# Must return: environment/nginx/nginx.conf (api_gateway), environment/auth-service/.env (6380),
#              environment/data-service/app.py (before_first_request),
#              environment/worker/celery_app.py (CELERY_BROKER_URL),
#              environment/api-gateway/main.py (validator)
# These are the BUG FILES — that is correct. No non-bug file should appear.

# ── D. Confirm solution/ and tests/ are NOT in environment/ ─────────────
ls microservice_dependency_hell@tasks.harborframework.com/environment/
# Must NOT contain: solve.sh, test_outputs.py, fix_*.sh

# ── E. Confirm complete structure ────────────────────────────────────────
find microservice_dependency_hell@tasks.harborframework.com/ -type f | sort
# Must include ALL of:
#   task.toml
#   instruction.md
#   environment/Dockerfile
#   environment/docker-compose.yml
#   environment/nginx/nginx.conf
#   environment/api-gateway/main.py
#   environment/api-gateway/requirements.txt
#   environment/auth-service/app.py
#   environment/auth-service/requirements.txt
#   environment/auth-service/.env
#   environment/data-service/app.py
#   environment/data-service/models.py
#   environment/data-service/requirements.txt
#   environment/worker/celery_app.py
#   environment/worker/tasks.py
#   environment/worker/requirements.txt
#   solution/solve.sh
#   tests/test.sh
#   tests/requirements.txt
#   tests/test_outputs.py

# ── F. Zip and submit ────────────────────────────────────────────────────
zip -r microservice_dependency_hell_submission.zip \
    microservice_dependency_hell@tasks.harborframework.com/

unzip -l microservice_dependency_hell_submission.zip | head -30

# Submit at: https://forms.gle/jJfsy546UKWJb9276
```

---

## Appendix A — Exact Error Messages Per Bug

These are the exact strings the agent will see in `docker compose logs`, used here for grader verification:

```
# Bug 1 — api-gateway (startup crash)
ImportError: cannot import name 'validator' from 'pydantic'
  (/usr/local/lib/python3.12/site-packages/pydantic/__init__.py)

# Bug 2 — auth-service (triggered on first login request)
redis.exceptions.ConnectionError: Error 111 connecting to redis:6380. Connection refused.

# Bug 3 — nginx (inside container's own error log, NOT in docker compose logs nginx)
# Run: docker exec <nginx-container-id> cat /var/log/nginx/error.log
[error] 1#1: host not found in upstream "api_gateway" in /etc/nginx/nginx.conf:5

# Bug 4 — data-service (startup crash)
AttributeError: 'Flask' object has no attribute 'before_first_request'

# Bug 5 — celery-worker (no crash — silent wrong-broker connection)
# Worker shows this in startup log — note amqp:// not redis://
.> transport:   amqp://guest:**@localhost//    ← Redis expected here
```

---

## Appendix B — Manual Quick-Test Script

Use this to manually verify the full stack after `solve.sh` completes:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== 1. Health ==="
curl -sf http://localhost:8080/health

echo ""
echo "=== 2. Login ==="
TOKEN=$(curl -sf -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"secret"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "Token obtained: ${TOKEN:0:30}..."

echo ""
echo "=== 3. Create Item ==="
curl -sf -X POST http://localhost:8080/data/items \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"manual-test","value":"blue"}'

echo ""
echo "=== 4. List Items ==="
curl -sf http://localhost:8080/data/items \
  -H "Authorization: Bearer $TOKEN"

echo ""
echo "=== 5. Enqueue Task ==="
curl -sf -X POST http://localhost:8080/data/notify \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"manual-hello"}'

echo ""
echo "=== Waiting 10s for worker... ==="
sleep 10

echo ""
echo "=== Worker Logs (last 10 lines) ==="
docker compose -f /app/docker-compose.yml logs celery-worker --tail=10 --no-color

echo ""
echo "=== All manual checks passed ==="
```

---

*This document is confidential and must not be shared on any public forum per the terms of the Bespoke Labs Take Home Test.*
