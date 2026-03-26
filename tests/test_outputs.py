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
