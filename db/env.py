from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.sql import text
from logging.config import fileConfig
import sys
import os

# Add our source path to the search paths for modules
src_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, src_path)

# Import our models and database objects
from mjcs.config import config as my_config
from mjcs.models.common import TableBase
from mjcs.models import *
if os.getenv('CASEHARVESTER_ENV') == 'production':
    my_config.initialize_from_environment('production')
else:
    my_config.initialize_from_environment('development')

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = TableBase.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = my_config.MJCS_DATABASE_URL
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = my_config.db_engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# Run idempotent SQL scripts
scripts_path = os.path.join(os.path.dirname(__file__), 'sql')
for file in os.listdir(scripts_path):
    if file.endswith('.sql'):
        print(f'Running SQL initialization script {file}')
        with open(os.path.join(scripts_path, file), 'r') as script:
            commands = script.read()
            with my_config.db_engine.begin() as conn:
                conn.execute(text(commands))