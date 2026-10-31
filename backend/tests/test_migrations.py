from alembic import command

from tests.conftest import alembic_config


def test_models_match_migrations():
    """Fails if a model changed without a migration."""
    command.check(alembic_config())
