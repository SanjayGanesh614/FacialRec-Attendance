# app/db/base.py
# ─────────────────────────────────────────────────────────────
# SQLAlchemy async engine and session factory.
# Import AsyncSessionLocal in dependencies.py only.
# Import Base in all models so Alembic can discover them.
# ─────────────────────────────────────────────────────────────

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ── Engine ─────────────────────────────────────────────────────────────────────
# pool_pre_ping=True: test connections before use — handles DB restarts
# echo=False in production; set to True for SQL query logging in dev
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,           # max persistent connections in pool
    max_overflow=20,        # extra connections allowed when pool is full
    echo=settings.DEBUG,    # log SQL when DEBUG=True in .env
)


# ── Session factory ────────────────────────────────────────────────────────────
# expire_on_commit=False: keep ORM objects accessible after commit
# (important for async — avoids lazy-load errors)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative base ───────────────────────────────────────────────────────────
# All ORM models inherit from this.
# Alembic imports Base.metadata to auto-generate migrations.
class Base(DeclarativeBase):
    pass
