from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import settings
from scripts.verify_deployment import schema_checks


def test_full_migration_chain_matches_models(test_engine, monkeypatch):
    # Distinct disposable schema, never the application's public schema.
    schema = "migration_chain_" + uuid4().hex
    with test_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = test_engine.url.update_query_dict({"options": f"-csearch_path={schema}"})
    monkeypatch.setattr(
        settings, "database_url", url.render_as_string(hide_password=False)
    )
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    engine = create_engine(url, poolclass=NullPool)
    try:
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        with engine.connect() as connection:
            result = schema_checks(connection)
            assert result["ok"], result
    finally:
        engine.dispose()
        with test_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
