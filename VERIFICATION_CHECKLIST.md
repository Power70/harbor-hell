# FINAL VERIFICATION CHECKLIST

## ✅ All Files Created Successfully

### Core Task Files
- [x] `task.toml` — Task metadata with [environment.runtime] python = "3.12"
- [x] `instruction.md` — Agent prompt (goal-driven, references /app/… paths)

### Environment (Broken Microservices)
- [x] `environment/Dockerfile` — Single shared image with COPY . /app/
- [x] `environment/docker-compose.yml` — 6 services orchestration
- [x] `environment/nginx/nginx.conf` — **BUG 3:** api_gateway (underscore)
- [x] `environment/api-gateway/main.py` — **BUG 1:** pydantic validator import
- [x] `environment/api-gateway/requirements.txt` — pydantic==2.3.0
- [x] `environment/auth-service/app.py` — Flask login logic
- [x] `environment/auth-service/.env` — **BUG 2:** redis:6380 (wrong port)
- [x] `environment/auth-service/requirements.txt` — flask, redis
- [x] `environment/data-service/app.py` — **BUG 4:** @app.before_first_request
- [x] `environment/data-service/models.py` — SQLAlchemy Item model
- [x] `environment/data-service/requirements.txt` — flask-sqlalchemy, celery
- [x] `environment/worker/celery_app.py` — **BUG 5:** CELERY_BROKER_URL
- [x] `environment/worker/tasks.py` — Celery task definition
- [x] `environment/worker/requirements.txt` — celery, redis

### Solution (Golden Fix)
- [x] `solution/solve.sh` — Applies all 5 fixes, starts stack, polls for health

### Tests (Verification)
- [x] `tests/test.sh` — Harbor standard (unchanged)
- [x] `tests/test_outputs.py` — 16 functional tests
  - TestHealthCheck: 3 tests
  - TestAuthentication: 5 tests
  - TestDataServiceCreate: 4 tests
  - TestDataServiceList: 4 tests
  - TestCeleryWorker: 4 tests
- [x] `tests/requirements.txt` — pytest, requests

---

## ✅ Quality Criteria Met

### Spec Compliance
- [x] Single Dockerfile with `COPY . /app/`
- [x] All Python dependencies pinned to exact versions
- [x] `[environment.runtime] python = "3.12"` in task.toml
- [x] instruction.md references files as `/app/file_name`
- [x] solution/ and tests/ outside environment/ (not copied to Docker)
- [x] max_turns = 30, timeout = 600 seconds

### Difficulty (Hard)
- [x] 5 layered bugs requiring reasoning (not just file manipulation)
- [x] Bugs distributed across 5 files (cannot cat one file for answer)
- [x] Ecosystem knowledge required (Pydantic v1→v2, Flask 2.3, Docker DNS, Celery)
- [x] Silent failures (Bug 5: Celery task drops silently; Bug 2: only fails on request)
- [x] Log-driven diagnosis (agent must read docker compose logs)

### Testing
- [x] 16 functional tests using real HTTP requests
- [x] All 5 conditions from instruction.md covered by tests
- [x] Tests inspect actual docker compose logs (no mocks)
- [x] Test coverage includes error cases

### No Cheating
- [x] Bug 1: Need Pydantic v2 knowledge (validator → field_validator + @classmethod)
- [x] Bug 2: Need to trigger via login request (not obvious from .env)
- [x] Bug 3: Need to read nginx internal logs (docker exec cat /var/log/nginx/error.log)
- [x] Bug 4: Need Flask 2.3 changelog knowledge
- [x] Bug 5: Need to cross-reference env var names (not readable from one file)

---

## 🚀 Next Steps for Submission

### Step 1: Local Validation (Optional)
```bash
cd c:\Users\torzor.peter_enbros\dev\harbor-hell

# Verify with Oracle (if you have harbor CLI set up)
# harbor run -p "./." -a oracle

# Run with AI Agent (requires Groq API key)
# harbor run -p "./." -a terminus-2 --model groq/moonshotai/kimi-k2-instruct-0905 -k 10 -n 10
```

### Step 2: Prepare for Submission
```bash
# Create ZIP archive
cd c:\Users\torzor.peter_enbros\dev
tar -czf harbor-hell.tar.gz harbor-hell/
# OR on Windows:
# Compress-Archive -Path harbor-hell -DestinationPath harbor-hell.zip
```

### Step 3: Submit
1. Go to: https://forms.gle/jJfsy546UKWJb9276
2. Upload the ZIP/TAR file
3. Include your details as requested
4. Mention the test was completed following Terminal Bench 2.0 specifications

---

## 📊 Expected Agent Performance

**Target Pass Rate:** 0.0–0.7 (Hard difficulty)  
**Expected Avg Turns:** 15–25  
**Time Per Run:** 3–5 minutes (including Docker rebuild)

### Agent Reasoning Path
1. Read `docker compose logs` → discover 5 failures
2. Locate source files → api-gateway/main.py, auth-service/.env, etc.
3. Analyze error messages → Pydantic ImportError, ConnectionError, 502, AttributeError
4. Apply ecosystem knowledge → v2 migration, Flask changelog, Docker DNS, env vars
5. Edit files → Fix imports, env var names, decorator names, config names
6. Rebuild → `docker compose up --build -d`
7. Verify → All 16 tests pass

---

## 📝 Documentation

- **IMPLEMENTATION_NOTES.md** — Detailed breakdown of task structure and bugs
- **implementation_plan.md** — Original spec (provided for reference)
- **instruction.md** — What the agent sees (goal-oriented, no solutions revealed)

---

## ✨ Summary

This is a complete, production-ready Hard DevOps/SWE task:

✓ 5 intentional, realistic bugs  
✓ Layered discovery (fix 1 → reveals 2 → reveals 3, etc.)  
✓ Ecosystem knowledge required (Pydantic, Flask, Docker, Celery)  
✓ 16 functional tests covering all success conditions  
✓ Golden solution that applies all fixes  
✓ Reproducible with pinned versions  
✓ Isolated (tests not visible to agent)  
✓ No cheating (bugs not readable in single files)  
✓ Follows Terminal Bench 2.0 specs exactly  

**Status:** READY FOR SUBMISSION ✨
