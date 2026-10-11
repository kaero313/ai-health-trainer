import ipaddress
import os
from functools import lru_cache
from pathlib import Path
import socket
import sys
from collections.abc import AsyncGenerator, Awaitable, Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urlsplit

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── 테스트 격리 ──────────────────────────────────────────────────────────────
# 1) 로컬 .env 대신 코드 기본값으로 테스트한다. compose가 backend/.env 전체를 컨테이너 환경변수로
#    넣고 Settings도 /app/.env를 읽으므로, app을 import하기 전에 Settings 필드와 같은 이름의 환경변수를
#    지우고 get_settings를 .env 파일을 읽지 않는 버전으로 바꾼다. 접속 위치인 인프라 주소만 남긴다.
#    그래서 로컬과 CI가 같은 설정으로 테스트한다.
# 2) Gemini 키는 가짜 값으로 둔다. 대역을 빠뜨린 테스트가 실제 Gemini를 호출·과금하지 않게 한다.
#    키가 비어 있으면 genai.Client 생성이 실패하므로 빈 값이 아니라 CI와 같은 가짜 값을 둔다.
# 3) pytest_configure가 루프백과 테스트용 PostgreSQL·Redis 외의 이름 해석·소켓 연결을 차단한다.
#    Gemini·공식 문서 URL 수집 같은 외부 호출이 테스트에 섞이면 호출 지점에서 즉시 실패한다.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core import config as app_config  # noqa: E402

INFRA_SETTINGS = ("DATABASE_URL", "DATABASE_URL_SYNC", "REDIS_URL", "OPENSEARCH_URL")
TEST_GEMINI_API_KEY = "dummy-key-for-test"
for _field_name in app_config.Settings.model_fields:
    if _field_name not in INFRA_SETTINGS:
        os.environ.pop(_field_name, None)
os.environ.pop("GOOGLE_API_KEY", None)
os.environ["GEMINI_API_KEY"] = TEST_GEMINI_API_KEY


@lru_cache
def _test_settings() -> app_config.Settings:
    return app_config.Settings(_env_file=None)


# app 모듈이 `from app.core.config import get_settings`로 가져가기 전에 바꿔야 한다
app_config.get_settings = _test_settings

import app.models  # noqa: F401,E402
from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.deps import get_ai_quota_service  # noqa: E402
from app.main import app  # noqa: E402

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

_ORIGINAL_CONNECT = socket.socket.connect
_ORIGINAL_CONNECT_EX = socket.socket.connect_ex
_ORIGINAL_GETADDRINFO = socket.getaddrinfo
_ALLOWED_TARGETS: set[tuple[str, int]] = set()
_ALLOWED_HOSTS: set[str] = set()
# 서비스 코드가 `except Exception`으로 차단 예외를 삼키면 테스트가 저하 경로로 통과할 수 있다.
# 그래서 차단 시도를 기록해 두고, 테스트가 끝날 때 기록이 있으면 그 테스트를 실패시킨다.
_BLOCKED_ATTEMPTS: list[str] = []
# OpenSearch는 테스트가 기대면 안 되는 인프라다. CI에서는 주소가 localhost:9200이라 루프백 허용에
# 걸려 연결 거부만 조용히 삼켜지므로, 로컬과 같게 드러나도록 루프백이어도 항상 차단한다.
_DENIED_TARGETS: set[tuple[str, int]] = set()


def _test_redis_url() -> str:
    return os.getenv("TEST_REDIS_URL") or get_settings().REDIS_URL


def _url_targets(urls: tuple[tuple[str, int], ...]) -> set[tuple[str, int]]:
    """URL들의 (host, port)와 그 해석 결과 IP."""
    targets: set[tuple[str, int]] = set()
    for url, default_port in urls:
        parts = urlsplit(url)
        if not parts.hostname:
            continue
        port = parts.port or default_port
        targets.add((parts.hostname, port))
        try:
            for info in _ORIGINAL_GETADDRINFO(parts.hostname, port, type=socket.SOCK_STREAM):
                targets.add((str(info[4][0]), port))
        except socket.gaierror:
            pass
    return targets


def _allowed_targets() -> set[tuple[str, int]]:
    """테스트가 접속해도 되는 (host, port): 테스트 DB·관리 DB·Redis."""
    return _url_targets((
        (TEST_DATABASE_URL, 5432),
        (TEST_ADMIN_DATABASE_URL, 5432),
        (_test_redis_url(), 6379),
    ))


def _denied_targets() -> set[tuple[str, int]]:
    """루프백이어도 차단할 (host, port): OpenSearch."""
    return _url_targets(((get_settings().OPENSEARCH_URL, 9200),))


def _as_port(port: object) -> int | None:
    try:
        return int(port)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _is_loopback(host: str) -> bool:
    if host in {"localhost", ""}:
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def _reject(host: str, port: object) -> None:
    _BLOCKED_ATTEMPTS.append(f"{host}:{port}")
    raise RuntimeError(
        f"테스트에서 외부 네트워크 접속을 차단했습니다: {host}:{port}. "
        "대역(fake·MockTransport·monkeypatch)을 쓰세요."
    )


def _check_address(address: object) -> None:
    # AF_UNIX 경로 같은 튜플이 아닌 주소는 네트워크 접속이 아니므로 검사하지 않는다
    if not isinstance(address, tuple) or len(address) < 2:
        return
    host, port = str(address[0]), int(address[1])
    if (host, port) in _DENIED_TARGETS or not (_is_loopback(host) or (host, port) in _ALLOWED_TARGETS):
        _reject(host, port)


def _guarded_connect(self, address):
    _check_address(address)
    return _ORIGINAL_CONNECT(self, address)


def _guarded_connect_ex(self, address):
    _check_address(address)
    return _ORIGINAL_CONNECT_EX(self, address)


def _guarded_getaddrinfo(host, port, *args, **kwargs):
    name = "" if host is None else (host.decode() if isinstance(host, bytes) else str(host))
    if (name, _as_port(port)) in _DENIED_TARGETS or not (_is_loopback(name) or name in _ALLOWED_HOSTS):
        _reject(name, port)
    return _ORIGINAL_GETADDRINFO(host, port, *args, **kwargs)


@pytest.fixture
def expect_network_block() -> list[str]:
    """차단을 일부러 확인하는 테스트용. 이 픽스처를 쓰는 테스트는 종료 시 차단 기록 검사에서 빠진다."""
    return _BLOCKED_ATTEMPTS


@pytest.fixture(autouse=True)
def _fail_on_blocked_network(request: pytest.FixtureRequest):
    _BLOCKED_ATTEMPTS.clear()
    yield
    attempts = sorted(set(_BLOCKED_ATTEMPTS))
    _BLOCKED_ATTEMPTS.clear()
    if attempts and "expect_network_block" not in request.fixturenames:
        pytest.fail(
            "테스트가 외부 네트워크 접속을 시도했습니다(서비스가 예외를 삼켰더라도 실패 처리): "
            f"{', '.join(attempts)}. 대역(fake·MockTransport·monkeypatch)을 쓰세요.",
            pytrace=False,
        )


def local_env_leaks() -> list[str]:
    """코드 기본값과 다른 비인프라 설정 이름. 값은 비밀일 수 있으므로 이름만 돌려준다."""
    settings = get_settings()
    return [
        name
        for name, field in app_config.Settings.model_fields.items()
        if name not in (*INFRA_SETTINGS, "GEMINI_API_KEY")
        and getattr(settings, name) != field.get_default(call_default_factory=True)
    ]


def pytest_configure(config: pytest.Config) -> None:
    if get_settings().GEMINI_API_KEY != TEST_GEMINI_API_KEY:
        raise pytest.UsageError("테스트 Settings에 가짜가 아닌 GEMINI_API_KEY가 남아 있습니다.")
    leaked = local_env_leaks()
    if leaked:
        raise pytest.UsageError(f"테스트 Settings에 로컬 .env 값이 남아 있습니다: {', '.join(leaked)}")
    _ALLOWED_TARGETS.clear()
    _ALLOWED_TARGETS.update(_allowed_targets())
    _ALLOWED_HOSTS.clear()
    _ALLOWED_HOSTS.update(host for host, _ in _ALLOWED_TARGETS)
    _DENIED_TARGETS.clear()
    _DENIED_TARGETS.update(_denied_targets() - _ALLOWED_TARGETS)
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex
    socket.getaddrinfo = _guarded_getaddrinfo


def pytest_unconfigure(config: pytest.Config) -> None:
    socket.socket.connect = _ORIGINAL_CONNECT
    socket.socket.connect_ex = _ORIGINAL_CONNECT_EX
    socket.getaddrinfo = _ORIGINAL_GETADDRINFO


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
