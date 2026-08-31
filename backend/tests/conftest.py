import os
from pathlib import Path
import sys
from collections.abc import AsyncGenerator, Awaitable, Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.core.deps import get_ai_quota_service
from app.main import app

TEST_DB_NAME = "health_trainer_test"
TEST_ADMIN_DATABASE_URL = os.getenv(
    "TEST_DATABASE_ADMIN_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/health_trainer_test",
)
TEST_DB_NAME = make_url(TEST_DATABASE_URL).database or TEST_DB_NAME


async def _create_test_database() -> None:
    admin_engine = create_async_engine(TEST_ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = :db_name AND pid <> pg_backend_pid()"
            ),
            {"db_name": TEST_DB_NAME},
        )
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
        await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    await admin_engine.dispose()


async def _drop_test_database() -> None:
    admin_engine = create_async_engine(TEST_ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = :db_name AND pid <> pg_backend_pid()"
            ),
            {"db_name": TEST_DB_NAME},
        )
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
    await admin_engine.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def manage_test_database() -> AsyncGenerator[None, None]:
    await _create_test_database()
    yield
    await _drop_test_database()


@pytest_asyncio.fixture
async def db_session(manage_test_database: None) -> AsyncGenerator[AsyncSession, None]:
    test_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    quota_service,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ai_quota_service] = lambda: quota_service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


@pytest.fixture
def quota_service():
    async def reserve(_db, trace, **_kwargs):
        trace.quota_status = "reserved"
        trace.quota_bucket = "2099-01-01@Asia/Seoul"
        trace.quota_timezone = "Asia/Seoul"
        trace.quota_limit = 30
        trace.quota_position = 1
        return SimpleNamespace(status="reserved", position=1, limit=30)

    async def consume(trace, **_kwargs):
        trace.quota_status = "consumed"

    async def release(trace, **_kwargs):
        trace.quota_status = "released"

    return SimpleNamespace(
        reserve=AsyncMock(side_effect=reserve),
        consume=AsyncMock(side_effect=consume),
        release=AsyncMock(side_effect=release),
    )


@pytest.fixture
def auth_headers() -> Callable[[str], dict[str, str]]:
    def _build_auth_headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    return _build_auth_headers


@pytest.fixture
def register_and_get_token() -> Callable[[AsyncClient, str], Awaitable[tuple[str, int]]]:
    async def _register(client: AsyncClient, email: str) -> tuple[str, int]:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
            },
        )
        assert response.status_code == 201
        payload = response.json()["data"]
        return payload["access_token"], payload["user"]["id"]

    return _register
