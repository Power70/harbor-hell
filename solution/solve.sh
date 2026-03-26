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
