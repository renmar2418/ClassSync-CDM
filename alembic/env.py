"""Alembic environment configuration for ClassSync:
AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Prepend project root and packages/contracts-py
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
contracts_dir = os.path.join(base_dir, "packages", "contracts-py")
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
if contracts_dir not in sys.path:
    sys.path.insert(0, contracts_dir)

from classync_contracts.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate support
target_metadata = Base.metadata

def get_database_url() -> str:
    """Resolve database URL from environment variable or alembic.ini fallback."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        # Standardize postgres:// to postgresql+psycopg:// if needed
        if env_url.startswith("postgres://"):
            env_url = env_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif env_url.startswith("postgresql://") and "+psycopg" not in env_url:
            env_url = env_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return env_url
    return config.get_main_option(
        "sqlalchemy.url",
        "postgresql+psycopg://classync:classync@localhost:5432/classync_db"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    is_sqlite = configuration["sqlalchemy.url"].startswith("sqlite")
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
