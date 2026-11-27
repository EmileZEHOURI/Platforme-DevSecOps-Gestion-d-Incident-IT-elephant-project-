"""Run real browser/API tests in a disposable PostgreSQL schema, never public."""

import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from uuid import uuid4

from redis.exceptions import RedisError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

frontend = Path(__file__).resolve().parents[1]
backend = frontend.parent / "backend"
sys.path.insert(0, str(backend))
raw = os.environ.get("TEST_DATABASE_URL", "")
if not raw:
    raise SystemExit(
        "TEST_DATABASE_URL is required (a dedicated PostgreSQL *_test database)."
    )
url = make_url(raw)
if url.get_backend_name() != "postgresql" or not (url.database or "").endswith("_test"):
    raise SystemExit("Refusing a database that is not PostgreSQL *_test.")
if (
    os.environ.get("DATABASE_URL")
    and url.database == make_url(os.environ["DATABASE_URL"]).database
):
    raise SystemExit("Test database must differ from application database.")
for port in (8017, 3017):
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(
                f"Port {port} is already in use; no existing service will be reused."
            )
schema = "e2e_" + uuid4().hex
admin = create_engine(url)
test_url = url.update_query_dict({"options": f"-csearch_path={schema}"})
os.environ.update(
    DATABASE_URL=test_url.render_as_string(hide_password=False),
    ENVIRONMENT="test",
    JWT_SECRET_KEY=secrets.token_urlsafe(48),
    JWT_REVOCATION_ENABLED="true",
    REDIS_URL=os.environ.get("E2E_REDIS_URL", "redis://127.0.0.1:6380/0"),
    CSRF_PROTECTION_ENABLED="true",
    FRONTEND_ORIGIN="http://127.0.0.1:3017",
)
from app.models import User  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.security.redis_client import get_redis_client  # noqa: E402

get_redis_client().ping()

engine = None
process = None
created = False
try:
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    created = True
    engine = create_engine(test_url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for role in (UserRole.USER, UserRole.TECHNICIAN, UserRole.ADMIN):
            session.add(
                User(
                    email=f"{role.value.lower()}@e2e.example.com",
                    full_name=f"E2E {role.value}",
                    role=role,
                    is_active=True,
                    password_hash=hash_password("e2e-only-password"),
                )
            )
        session.commit()
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    with open(frontend / "test-results-api.log", "w", encoding="utf-8") as log:

        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8017",
            ],
            cwd=backend,
            stdout=log,
            stderr=log,
            creationflags=flags,
        )

        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError(
                    "Isolated API did not start; see test-results-api.log."
                )
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:8017/health", timeout=1
                ) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("Isolated API startup timed out.")
        result = subprocess.run(
            ["node", "node_modules/@playwright/test/cli.js", "test"], cwd=frontend
        )
        exit_code = result.returncode
finally:
    if process is not None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    if engine is not None:
        # Only keys belonging to the isolated schema and random signing key.
        try:
            with engine.connect() as conn:
                for digest in conn.scalars(text("SELECT digest FROM revoked_tokens")):
                    get_redis_client().delete(f"auth:revoked:{digest}")
        except RedisError:
            # Cache entries still expire automatically; SQL cleanup must proceed.
            print("Redis cleanup unavailable; isolated keys will expire by TTL.", file=sys.stderr)
        finally:
            engine.dispose()
    if created:
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()
sys.exit(exit_code)
