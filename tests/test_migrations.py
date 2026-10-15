from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command


def test_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/migration.db"
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(url)
    assert {"answers", "documents", "passages", "reviews", "changes"} <= set(
        inspect(engine).get_table_names()
    )
    command.downgrade(Config("alembic.ini"), "base")
    assert "passages" not in inspect(engine).get_table_names()
    engine.dispose()
