import importlib.util
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text


def test_revocation_migration_upgrade_downgrade(test_engine):
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/c41f9a2d7e10_add_revoked_tokens.py"
    )
    spec = importlib.util.spec_from_file_location("revocation_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = "migration_" + uuid4().hex
    with test_engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            with Operations.context(MigrationContext.configure(connection)):
                module.upgrade()
                assert inspect(connection).has_table("revoked_tokens", schema=schema)
                indexes = inspect(connection).get_indexes(
                    "revoked_tokens", schema=schema
                )
                assert any(i["name"] == "ix_revoked_tokens_expires_at" for i in indexes)
                module.downgrade()
                assert not inspect(connection).has_table(
                    "revoked_tokens", schema=schema
                )
        finally:
            transaction.rollback()
