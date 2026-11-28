"""Read-only runtime verification. Run inside the target service; never prints URLs."""

import hashlib
import json
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.models import Base


def schema_checks(connection):
    inspector = inspect(connection)
    context = MigrationContext.configure(
        connection,
        opts={
            "compare_type": True,
            "include_object": lambda obj, name, kind, reflected, compare_to: (
                kind != "table" or name in Base.metadata.tables
            ),
        },
    )
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    expected_heads = set(ScriptDirectory.from_config(config).get_heads())
    applied_heads = set(context.get_current_heads())
    differences = compare_metadata(context, Base.metadata)
    tables = {}
    for table in Base.metadata.sorted_tables:
        exists = inspector.has_table(table.name)
        checks = {c.name for c in table.constraints if isinstance(c, CheckConstraint)}
        actual_checks = (
            {c["name"] for c in inspector.get_check_constraints(table.name)}
            if exists
            else set()
        )
        expected_fk = {
            (
                tuple(c.column_keys),
                tuple(e.target_fullname for e in c.elements),
                c.ondelete,
            )
            for c in table.foreign_key_constraints
        }
        actual_fk = (
            {
                (
                    tuple(c["constrained_columns"]),
                    tuple(
                        c["referred_table"] + "." + col for col in c["referred_columns"]
                    ),
                    c.get("options", {}).get("ondelete"),
                )
                for c in inspector.get_foreign_keys(table.name)
            }
            if exists
            else set()
        )
        tables[table.name] = {
            "exists": exists,
            "missing_checks": sorted(checks - actual_checks),
            "foreign_keys_match": actual_fk == expected_fk,
        }
    ok = (
        not differences
        and applied_heads == expected_heads
        and all(
            t["exists"] and not t["missing_checks"] and t["foreign_keys_match"]
            for t in tables.values()
        )
    )
    return {
        "ok": ok,
        "applied_heads": sorted(applied_heads),
        "expected_heads": sorted(expected_heads),
        "metadata_difference_count": len(differences),
        "tables": tables,
    }


def verify():
    try:
        from app.core.config import settings
        from app.security.redis_client import get_redis_client
    except Exception as error:
        # Pydantic errors can include the original environment values.
        return {"configuration_error": type(error).__name__}

    report = {
        "environment": settings.environment,
        "csrf_enabled": settings.environment == "production"
        or settings.csrf_protection_enabled,
        "rate_limiting_enabled": settings.environment == "production"
        or settings.login_rate_limit_enabled,
        "revocation_enabled": settings.jwt_revocation_required,
        "sql_echo_enabled": settings.sql_echo,
    }
    engine = None
    try:
        url = make_url(settings.database_url)
        fingerprint = hashlib.sha256(
            f"{url.host}:{url.port}/{url.database}".encode()
        ).hexdigest()[:16]
        report["database_target_fingerprint"] = fingerprint
        report["database_driver"] = url.drivername
        engine = create_engine(
            url, pool_pre_ping=True, echo=False, connect_args={"connect_timeout": 5}
        )
        with engine.connect() as connection, connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SET LOCAL statement_timeout = '10000'"))
            connection.execute(text("SELECT 1"))
            report["postgresql"] = {
                "connected": True,
                "server_version": connection.execute(
                    text("SHOW server_version")
                ).scalar_one(),
            }
            report["schema"] = schema_checks(connection)
    except Exception as error:
        # Exception messages may contain connection strings or query parameters.
        report["database_error"] = type(error).__name__
    finally:
        if engine is not None:
            engine.dispose()
    try:
        report["redis"] = {"ping": bool(get_redis_client().ping())}
    except Exception as error:
        report["redis"] = {"ping": False, "error_type": type(error).__name__}
    return report


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, indent=2))
    raise SystemExit(
        0 if result.get("schema", {}).get("ok") and result.get("redis", {}).get("ping") else 1
    )
