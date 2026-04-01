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
