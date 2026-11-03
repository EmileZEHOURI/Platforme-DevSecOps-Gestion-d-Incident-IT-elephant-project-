import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.repositories import UserRepository
from app.security import hash_password


@pytest.fixture(scope="session")
def test_engine():
    raw_url = os.environ.get("TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("TEST_DATABASE_URL requis pour les tests PostgreSQL (base *_test).")
    url = make_url(raw_url)
    if url.get_backend_name() != "postgresql" or not (url.database or "").endswith(
        "_test"
    ):
        pytest.fail(
            "TEST_DATABASE_URL doit cibler une base PostgreSQL terminant par _test."
        )
    if url.database == make_url(settings.database_url).database:
        pytest.fail("La base de test doit être distincte de la base applicative.")

    schema = f"pytest_{uuid4().hex}"
    admin = create_engine(url, echo=False)
    engine = None
    created = False
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        created = True
        engine = create_engine(
            url, echo=False, connect_args={"options": f"-csearch_path={schema}"}
        )
        Base.metadata.create_all(engine)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        if created:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def db_session(test_engine):
    with test_engine.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        ) as session:
            try:
                yield session
            finally:
                session.close()
                transaction.rollback()


@pytest.fixture(autouse=True)
def isolated_api_database(request):
    previous = app.dependency_overrides.copy()
    session = None
    if request.node.path.parent.name == "api" or "db_session" in request.fixturenames:
        session = request.getfixturevalue("db_session")

    def override_db():
        if session is None:
            raise RuntimeError("Le test doit demander la fixture db_session.")
        yield session

    app.dependency_overrides[get_db] = override_db
    old_environment = settings.environment
    settings.environment = "test"
    try:
        yield
    finally:
        settings.environment = old_environment
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture
def test_user(db_session):
    user = UserRepository(db_session).create(
        email="test@example.com",
        password_hash=hash_password("password"),
        full_name="Test User",
    )
    db_session.commit()
    return user
