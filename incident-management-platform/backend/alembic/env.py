from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.models import Base

# Objet de configuration Alembic correspondant à alembic.ini.
config = context.config

# Utilise la DATABASE_URL chargée depuis le fichier .env.
#
# Le remplacement de "%" évite les problèmes d'interpolation
# du format de configuration INI.
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("%", "%%"),
)

# Configure les logs définis dans alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Contient les tables, colonnes, relations et contraintes
# déclarées dans les modèles SQLAlchemy.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Génère les migrations sans ouvrir directement de connexion."""

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Exécute les migrations avec une connexion PostgreSQL."""

    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {},
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()