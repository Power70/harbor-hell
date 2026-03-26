# Microservice Dependency Hell

Confidential assessment project for the Bespoke Labs Senior DevOps/Backend SWE take-home.

Do not share this repository or its contents publicly.

## Overview

This project implements a Hard Terminal Bench 2.0 task where an AI agent must diagnose and repair a broken Python microservices stack inside Docker Compose.

The task is intentionally designed to require real debugging and reasoning, including:

- dependency migration breakage
- environment/config mismatch
- service discovery/proxy mismatch
- framework API removal after upgrade
- silent worker misconfiguration

## Task Goal

An agent receives [instruction.md](instruction.md) and access to the files under [environment](environment). The agent must repair the stack so all functional checks pass.

Success criteria are encoded in:

- [instruction.md](instruction.md)
- [tests/test_outputs.py](tests/test_outputs.py)

## Repository Structure

- [task.toml](task.toml): Terminal Bench task metadata and runtime configuration
- [instruction.md](instruction.md): Prompt shown to the agent
- [environment](environment): Intentionally broken runtime environment the agent works in
- [solution](solution): Golden solution scripts used by Oracle
- [tests](tests): Functional verification logic
- [implementation_plan.md](implementation_plan.md): Full implementation design/spec used to build this task
- [IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md): Internal summary notes
- [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md): Internal QA checklist

## Architecture

Services in [environment/docker-compose.yml](environment/docker-compose.yml):

- nginx reverse proxy (port 8080 externally)
- api-gateway (FastAPI)
- auth-service (Flask + Redis)
- data-service (Flask + SQLAlchemy)
- celery-worker (Celery)
- redis

All Python services are built from the single [environment/Dockerfile](environment/Dockerfile), as required by the take-home instructions.

## Intentional Bug Set

The environment contains 5 layered failures distributed across multiple services:

1. Pydantic v2 validator import break in [environment/api-gateway/main.py](environment/api-gateway/main.py)
2. Wrong Redis port in [environment/auth-service/.env](environment/auth-service/.env)
3. Nginx upstream service-name mismatch in [environment/nginx/nginx.conf](environment/nginx/nginx.conf)
4. Removed Flask API usage in [environment/data-service/app.py](environment/data-service/app.py)
5. Wrong Celery broker env var in [environment/worker/celery_app.py](environment/worker/celery_app.py)

These are intended and should remain in the environment baseline.

## Prerequisites

Install and verify the following on your machine:

- Docker Desktop (running)
- Python 3.12 support
- uv package manager
- Harbor CLI
- Groq API key (for AI-agent runs)

Recommended shell: WSL (Linux shell) for best compatibility with Harbor and shell scripts.

## Local Setup

Run from the project root.

WSL/Linux style setup:

```bash
# 1) Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2) Project environment
uv init
uv venv --python 3.12
source .venv/bin/activate

# 3) Harbor CLI
uv tool install harbor
harbor --version

# 4) Groq SDK
uv pip install groq

# 5) API key
echo 'GROQ_API_KEY="your_groq_api_key"' > .env
export GROQ_API_KEY="your_groq_api_key"

# 6) Docker check
docker info
```

PowerShell equivalent for API key:

```powershell
$env:GROQ_API_KEY = "your_groq_api_key"
Set-Content -Path .env -Value 'GROQ_API_KEY="your_groq_api_key"'
```

## How to Run Validation

Important: Run Harbor commands from the parent directory of this task folder.

Assuming this repo folder is harbor-hell under your dev directory:

```bash
cd /mnt/c/Users/torzor.peter_enbros/dev
```

### 1) Oracle Run (required)

Oracle executes [solution/solve.sh](solution/solve.sh) and then runs [tests/test.sh](tests/test.sh).

```bash
harbor run -p "./harbor-hell" -a oracle
```

Expected result:

- Oracle passes
- All tests in [tests/test_outputs.py](tests/test_outputs.py) pass

### 2) Agent Run (required for difficulty)

Use the requested model and run count:

```bash
harbor run \
	-p "./harbor-hell" \
	-a terminus-2 \
	--model groq/moonshotai/kimi-k2-instruct-0905 \
	-k 10 \
	-n 10
```

Expected difficulty target:

- pass_rate must be greater than 0.0 and less than 0.7

Recommended workflow:

- first run a quick smoke test with smaller k (for example k=2, n=2)
- then run the required k=10, n=10

## Manual Functional Spot Check (optional)

If you want to inspect behavior directly with Docker before Harbor:

```bash
cd environment
docker compose up --build -d
docker compose ps
docker compose logs --no-color | head -300
```

The baseline environment is intentionally broken; failures are expected until fixes are applied.

## Test Suite Coverage

[tests/test_outputs.py](tests/test_outputs.py) includes 16 functional tests grouped by requirement:

- Health checks
- Authentication flow
- Data creation flow
- Data listing flow
- Celery worker processing verification

The tests use real HTTP requests and container/log checks, not mocks.

## Quality and Compliance Checklist

This implementation satisfies the take-home constraints:

- task contains required files: [task.toml](task.toml), [instruction.md](instruction.md), [environment](environment), [solution](solution), [tests](tests)
- [task.toml](task.toml) includes environment.runtime python 3.12
- one root Dockerfile in [environment/Dockerfile](environment/Dockerfile)
- pinned versions used across base image and Python dependencies
- tests are functional and cover instruction requirements
- test logic is outside environment folder
- no hardcoded answer in instruction text

## Troubleshooting

If Harbor/Oracle fails, use this order:

1. Confirm Docker is running and healthy with docker info
2. Confirm Harbor is installed and visible in PATH with harbor --version
3. Confirm GROQ_API_KEY is exported in the shell that runs Harbor
4. Re-run Oracle and inspect logs
5. Validate file structure from project root

Helpful commands:

```bash
# from project root
find . -maxdepth 3 -type f | sort

# from environment folder
docker compose ps
docker compose logs --no-color --tail=200
```

## Submission Workflow

1. Run Oracle and ensure it passes.
2. Run agent evaluation with k=10, n=10 and capture the report.
3. Zip the entire task folder.
4. Submit at the official form:

https://forms.gle/jJfsy546UKWJb9276

Zip examples:

```powershell
Compress-Archive -Path .\harbor-hell -DestinationPath .\harbor-hell.zip -Force
```

```bash
zip -r harbor-hell.zip harbor-hell
```

## Confidentiality and Originality

Per assessment rules:

- keep this task confidential
- do not publish or share externally
- do not reuse existing public task content
- maintain originality of scenario and implementation

## Contact

For non-trivial take-home clarification questions:

- email: projects@bespokelabs.ai
- subject: Take Home Test Doubts