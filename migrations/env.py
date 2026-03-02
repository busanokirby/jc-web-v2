"""Alembic environment configuration for Flask-SQLAlchemy."""
from __future__ import with_statement
import logging
from logging.config import fileConfig

from flask import current_app
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

logger = logging.getLogger('alembic.env')
target_metadata = current_app.extensions['sqlalchemy'].metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = current_app.config['SQLALCHEMY_DATABASE_URI']
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    def process_revision_directives(ctx, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    engine = engine_from_config(
        {'sqlalchemy.url': current_app.config['SQLALCHEMY_DATABASE_URI']},
        prefix='sqlalchemy.',
        poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=process_revision_directives,
        **current_app.extensions['migrate'].configure_args
    )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()