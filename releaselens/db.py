import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from releaselens.models import Base


def database(url: str | None = None):
    url = url or os.getenv("DATABASE_URL", "sqlite:///./releaselens.db")
    options = {}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            options["poolclass"] = StaticPool
    engine = create_engine(url, **options)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    return engine, sessionmaker(engine, expire_on_commit=False)


def create_local_schema(engine):
    if engine.dialect.name != "sqlite":
        raise RuntimeError("Use alembic upgrade head for PostgreSQL")
    Base.metadata.create_all(engine)
