"""Shared pytest fixtures.

Tests run against an in-memory SQLite database (async) so they need no external
services. The app's ``get_session`` dependency is overridden to use a per-test
session bound to a shared in-memory engine.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

# Import models so their tables register on Base.metadata.
import app.models  # noqa: F401
import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import get_session
from app.main import app as fastapi_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[object]:
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine: object) -> AsyncIterator[AsyncSession]:
    maker = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)  # type: ignore[arg-type]
    async with maker() as s:
        yield s


@pytest_asyncio.fixture
async def client(engine: object) -> AsyncIterator[AsyncClient]:
    maker = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)  # type: ignore[arg-type]

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        async with maker() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    fastapi_app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _fast_argon2(monkeypatch: pytest.MonkeyPatch) -> None:
    """Speed up argon2 hashing in tests with low cost parameters."""
    import app.core.security as security
    from passlib.context import CryptContext

    ctx = CryptContext(
        schemes=["argon2"],
        deprecated="auto",
        argon2__time_cost=1,
        argon2__memory_cost=8,
        argon2__parallelism=1,
    )
    monkeypatch.setattr(security, "_pwd_context", ctx)
