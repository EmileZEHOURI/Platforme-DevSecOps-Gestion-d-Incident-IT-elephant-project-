"""Run published images in a disposable Compose project; never build locally."""
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
import httpx

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "incident-ghcr-test"
DOCKER = shutil.which("docker") or "C:/Program Files/Docker/Docker/resources/bin/docker.exe"
env = os.environ.copy()
env["PATH"] = str(Path(DOCKER).parent) + os.pathsep + env.get("PATH", "")
env.update(GHCR_TEST_DB_PASSWORD=secrets.token_hex(32), GHCR_TEST_JWT=secrets.token_hex(48), GHCR_TEST_PASSWORD=secrets.token_urlsafe(32))
OUT = ROOT / "docs/ghcr-validation"
OUT.mkdir(parents=True, exist_ok=True)
results = {}
def run(args, input=None, check=True):
    r = subprocess.run(args, input=input, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, cwd=ROOT)
    if check and r.returncode:
        raise RuntimeError(f"Command failed ({r.returncode}): {args[:4]}\n{r.stderr[-3000:]}")
    return r
def inventory():
    return run([DOCKER, "ps", "-a", "--format", "{{.ID}}|{{.Names}}|{{.Status}}", "--filter", "label=com.docker.compose.project=incident-management-platform"]).stdout
baseline = inventory()
results["main_before"] = baseline
if run([DOCKER, "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}"]).stdout.strip():
    raise RuntimeError("Temporary project already exists; refusing reuse.")
for resource in ("volume", "network"):
    if run([DOCKER, resource, "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"]).stdout.strip():
        raise RuntimeError("Temporary resources already exist; refusing reuse.")
for port in (3018, 8019):
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0: raise RuntimeError(f"Port {port} occupied.")
images = {}
for name in ("backend", "frontend"):
    tag = f"ghcr.io/emilezehouri/incident-{name}:latest"
    meta = json.loads(run([DOCKER, "image", "inspect", tag]).stdout)[0]
    images[name] = meta["RepoDigests"][0]
    results[name] = {k: meta[k] for k in ("Id", "RepoDigests", "Architecture", "Os", "Created")}
    results[name]["labels"] = meta["Config"].get("Labels")
def var(name): return "$" + "{" + name + "}"
settings = {
 "ENVIRONMENT": "development",
 "DATABASE_URL": "postgresql+psycopg://ghcr_test:" + var("GHCR_TEST_DB_PASSWORD") + "@db:5432/incident_ghcr_test",
 "REDIS_URL": "redis://redis:6379/0", "JWT_SECRET_KEY": var("GHCR_TEST_JWT"),
 "JWT_REVOCATION_ENABLED": "true", "LOGIN_RATE_LIMIT_ENABLED": "true",
 "CSRF_PROTECTION_ENABLED": "true", "FRONTEND_ORIGIN": "http://localhost:3018"}
def health(test): return {"test": test, "interval": "3s", "timeout": "4s", "retries": 30}
def healthy(name): return {name: {"condition": "service_healthy"}}
compose = {"services": {
 "db": {"image": "postgres:17-alpine", "environment": {"POSTGRES_USER": "ghcr_test", "POSTGRES_PASSWORD": var("GHCR_TEST_DB_PASSWORD"), "POSTGRES_DB": "incident_ghcr_test"},
        "volumes": ["postgres_data:/var/lib/postgresql/data"], "healthcheck": health(["CMD-SHELL", "pg_isready -U ghcr_test -d incident_ghcr_test"])},
 "redis": {"image": "redis:7-alpine", "command": ["redis-server", "--save", "", "--appendonly", "no"], "volumes": ["redis_data:/data"], "healthcheck": health(["CMD", "redis-cli", "ping"])},
 "migrate": {"image": images["backend"], "environment": settings, "depends_on": healthy("db"), "command": ["alembic", "upgrade", "head"], "restart": "no"},
 "backend": {"image": images["backend"], "environment": settings, "ports": ["127.0.0.1:8019:8000"],
             "depends_on": {**healthy("db"), **healthy("redis"), "migrate": {"condition": "service_completed_successfully"}},
             "healthcheck": health(["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"])},
 "frontend": {"image": images["frontend"], "environment": {"API_URL": "http://backend:8000", "HOSTNAME": "0.0.0.0", "NODE_ENV": "production", "NEXT_TELEMETRY_DISABLED": "1"},
              "ports": ["127.0.0.1:3018:3000"], "depends_on": healthy("backend"),
              "healthcheck": health(["CMD", "node", "-e", "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.status<500?0:1)).catch(()=>process.exit(1))"])}
}, "volumes": {"postgres_data": {}, "redis_data": {}}}
temporary = Path(tempfile.mkdtemp(prefix="incident-ghcr-"))
browser_dir = ROOT / "frontend" / (".ghcr-test-" + secrets.token_hex(4))
browser_dir.mkdir()
config = temporary / "compose.json"
config.write_text(json.dumps(compose), encoding="utf-8")
(OUT / "compose.json").write_text(json.dumps(compose, indent=2), encoding="utf-8")
cmd = [DOCKER, "compose", "-p", PROJECT, "-f", str(config)]
def dc(*args, **kwargs): return run(cmd + list(args), **kwargs)
def wait_http(url):
    for _ in range(60):
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200: return
        except Exception: time.sleep(1)
    raise RuntimeError("HTTP check failed: " + url)
try:
    print("Starting pinned GHCR images, without building.", flush=True)
    started = dc("up", "-d", "--no-build", "--wait", "--wait-timeout", "180")
    (OUT / "startup.log").write_text(started.stdout + started.stderr, encoding="utf-8")
    results["started"] = dc("ps", "-a", "--format", "json").stdout
    urls = ["http://127.0.0.1:8019/health", "http://127.0.0.1:8019/health/database", "http://localhost:3018", "http://localhost:3018/api/backend/health"]
    for url in urls: wait_http(url)
    results["http"] = {url: 200 for url in urls}
    migration = dc("ps", "-a", "-q", "migrate").stdout.strip()
    assert run([DOCKER, "inspect", migration, "--format", "{{.State.ExitCode}}"]).stdout.strip() == "0"
    print("Healthchecks and migrations passed. Seeding temporary database.", flush=True)
    seed = """
import sys
from app.core.database import SessionLocal
from app.models import User
from app.models.enums import UserRole
from app.security import hash_password
password = sys.stdin.readline().strip()
with SessionLocal() as session:
    for role in (UserRole.USER, UserRole.TECHNICIAN, UserRole.ADMIN):
        session.add(User(email=f"{role.value.lower()}@e2e.example.com", full_name=f"E2E {role.value}", role=role, is_active=True, password_hash=hash_password(password)))
    session.commit()
"""
    dc("exec", "-T", "backend", "python", "-c", seed, input=env["GHCR_TEST_PASSWORD"] + "\n")
    spec = (ROOT / "frontend/e2e/lifecycle.spec.ts").read_text(encoding="utf-8")
    spec = spec.replace("http://127.0.0.1:3017", "http://localhost:3018").replace('"e2e-only-password"', 'process.env.GHCR_TEST_PASSWORD!')
    (browser_dir / "lifecycle.spec.ts").write_text(spec, encoding="utf-8")
    (browser_dir / "playwright.config.ts").write_text("""
import { defineConfig } from "@playwright/test";
export default defineConfig({
 testDir: ".", testMatch: "lifecycle.spec.ts", workers: 1, retries: 0, timeout: 90000,
 expect: { timeout: 15000 }, reporter: "list",
 use: { baseURL: "http://localhost:3018", browserName: "chromium", channel: "msedge", trace: "off", screenshot: "off" }
});
""", encoding="utf-8")
    print("Running browser lifecycle against GHCR on 3018.", flush=True)
    test = run(["node", str(ROOT / "frontend/node_modules/@playwright/test/cli.js"), "test", "--config", str(browser_dir / "playwright.config.ts"), "--output", str(temporary / "test-results")], check=False)
    (OUT / "playwright.log").write_text(test.stdout + test.stderr, encoding="utf-8")
    results["playwright_exit_code"] = test.returncode
    print(test.stdout[-2000:], flush=True)
    if test.returncode: raise RuntimeError("Browser lifecycle failed; see playwright.log")
    print("Testing PostgreSQL persistence and revocation after app/Redis restart.", flush=True)
    with httpx.Client(base_url="http://localhost:3018/api/backend", headers={"Origin": "http://localhost:3018"}, timeout=20) as client:
        login = client.post("/auth/login", json={"email": "user@e2e.example.com", "password": env["GHCR_TEST_PASSWORD"]})
        assert login.status_code == 200
        token = client.cookies.get("access_token")
        assert token
        created = client.post("/incidents", json={"title": "GHCR persistence check", "description": "Incident temporaire pour verifier la persistance PostgreSQL.", "category": "ANOMALY", "priority": "MEDIUM"})
        assert created.status_code == 201
        incident_id = created.json()["id"]
        assert client.post("/auth/logout").status_code == 200
        assert client.get("/auth/me", headers={"Cookie": "access_token=" + token}).status_code == 401
        dc("stop", "frontend", "backend")
        dc("restart", "redis")
        migration_again = dc("run", "--rm", "--no-deps", "migrate")
        (OUT / "migration-rerun.log").write_text(migration_again.stdout + migration_again.stderr, encoding="utf-8")
        dc("up", "-d", "--no-build", "--wait", "--wait-timeout", "180", "backend", "frontend")
        wait_http("http://localhost:3018/api/backend/health")
        assert client.get("/auth/me", headers={"Cookie": "access_token=" + token}).status_code == 401
        assert client.post("/auth/login", json={"email": "user@e2e.example.com", "password": env["GHCR_TEST_PASSWORD"]}).status_code == 200
        persisted = client.get(f"/incidents/{incident_id}")
        assert persisted.status_code == 200 and persisted.json()["title"] == "GHCR persistence check"
        results["persistence"] = {"incident_id": incident_id, "incident": True, "account": True, "migrations_rerun": True, "revoked_jwt_after_redis_restart": True}
    results["outcome"] = "VALIDÉ"
except Exception as error:
    results["outcome"] = "NON VALIDÉ"
    results["error"] = str(error)
    print(str(error), flush=True)
finally:
    logs = dc("logs", "--no-color", check=False)
    (OUT / "containers.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
    results["before_cleanup"] = dc("ps", "-a", "--format", "json").stdout
    volume_names = run([DOCKER, "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"]).stdout.splitlines()
    if any(not name.startswith(PROJECT + "_") for name in volume_names): raise RuntimeError("Unexpected volume name; refusing cleanup.")
    cleaned = dc("down", "--volumes", "--remove-orphans", check=False)
    results["cleanup_exit_code"] = cleaned.returncode
    results["remaining_test_containers"] = run([DOCKER, "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}"]).stdout.strip()
    results["remaining_test_volumes"] = run([DOCKER, "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"]).stdout.strip()
    results["remaining_test_networks"] = run([DOCKER, "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"]).stdout.strip()
    results["main_after"] = inventory()
    before_ids = {line.split("|")[0] for line in baseline.splitlines()}
    after_ids = {line.split("|")[0] for line in results["main_after"].splitlines()}
    results["main_container_ids_unchanged"] = before_ids == after_ids
    for folder, parent in ((browser_dir, ROOT / "frontend"), (temporary, Path(tempfile.gettempdir()))):
        assert folder.resolve().parent == parent.resolve() and folder.name.startswith((".ghcr-test-", "incident-ghcr-"))
        shutil.rmtree(folder)
    if cleaned.returncode or before_ids != after_ids or any(results.get(key) for key in ("remaining_test_containers", "remaining_test_volumes", "remaining_test_networks")):
        results["outcome"] = "NON VALIDÉ"
    (OUT / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Result: " + results.get("outcome", "PARTIELLEMENT VALIDÉ"), flush=True)
    print("Cleanup exit: " + str(cleaned.returncode), flush=True)
    print("Main container IDs unchanged: " + str(before_ids == after_ids), flush=True)

raise SystemExit(0 if results.get("outcome") == "VALIDÉ" else 1)
