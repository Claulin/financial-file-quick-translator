from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


def make_engine(sqlite_path: str):
    return create_engine(
        f"sqlite+pysqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )


def make_session_factory(engine):
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
