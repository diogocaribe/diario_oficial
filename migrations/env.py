from logging.config import fileConfig

from alembic import context

from diario_oficial.settings import Settings
from sqlalchemy import engine_from_config, pool, MetaData, text
from sqlalchemy.schema import CreateSchema

# import sys
# import os
# Adiciona o diretório raiz do projeto ao sys.path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from diario_oficial.database.configs.base import Base

from diario_oficial.database.entity.ato_bruto import AtoBruto
from diario_oficial.database.entity.diario_oficial_bruto import DiarioOficialBruto
from diario_oficial.database.entity.dominio import Poder

from diario_oficial.database.configs.connection import DBConnectionHandler
from diario_oficial.settings import Settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option('sqlalchemy.url', Settings().DATABASE_URL)


# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
convention = {
    'ix': 'ix_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s',
}
metadata = MetaData(naming_convention=convention)
target_metadata = [DiarioOficialBruto.metadata]
# target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Create the database if it doesn't exist
    with DBConnectionHandler() as conn:
        result = conn.get_engine.execute(
            text(f'SELECT 1 FROM pg_database WHERE datname = :database_name'),
            {'database_name': Settings().DATABASE},
        )
        if not result.fetchone():
            conn.execute(text(f'CREATE DATABASE {Settings().DATABASE}'))

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, include_schemas=True
        )
        # Adicionando o schema que exite no modelo
        # Isso aqui não ficou muito bom.
        connection.execute(CreateSchema('processing', if_not_exists=True))
        connection.execute(CreateSchema('dominio', if_not_exists=True))

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
