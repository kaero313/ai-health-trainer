"""테스트 격리 회귀: 실제 Gemini 키와 외부 네트워크 접속이 테스트에 섞이지 않는다.

격리 장치는 tests/conftest.py에 있다. 이 테스트는 실제 외부 접속을 시도하지 않는다.
차단은 이름 해석·소켓 연결 직전에 일어나므로 패킷이 나가지 않는다.
"""

import os
import socket
from urllib.parse import urlsplit

import pytest

from app.core.config import get_settings

DUMMY_KEY = "dummy-key-for-test"


def test_settings_use_dummy_gemini_key() -> None:
    assert get_settings().GEMINI_API_KEY == DUMMY_KEY
    assert os.environ["GEMINI_API_KEY"] == DUMMY_KEY
    assert "GOOGLE_API_KEY" not in os.environ


def test_settings_use_code_defaults_instead_of_local_env() -> None:
    """인프라 주소와 가짜 키 외의 설정은 로컬 .env가 아니라 코드 기본값이어야 한다."""
    infra = {"DATABASE_URL", "DATABASE_URL_SYNC", "REDIS_URL", "OPENSEARCH_URL", "GEMINI_API_KEY"}
    settings = get_settings()
    differing = [
        name
        for name, field in type(settings).model_fields.items()
        if name not in infra and getattr(settings, name) != field.get_default(call_default_factory=True)
    ]
    # 값은 비밀일 수 있으므로 실패 메시지에는 이름만 남긴다
    assert not differing, f"로컬 값이 섞인 설정: {', '.join(differing)}"
    for name in type(settings).model_fields:
        if name not in infra:
            assert name not in os.environ, f"환경변수가 남아 있음: {name}"


def test_external_hostname_is_blocked_before_dns(expect_network_block: list[str]) -> None:
    with pytest.raises(RuntimeError, match="외부 네트워크 접속을 차단"):
        socket.getaddrinfo("generativelanguage.googleapis.com", 443)
    assert expect_network_block == ["generativelanguage.googleapis.com:443"]


def test_external_ip_connect_is_blocked(expect_network_block: list[str]) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(RuntimeError, match="외부 네트워크 접속을 차단"):
            sock.connect(("8.8.8.8", 443))
        with pytest.raises(RuntimeError, match="외부 네트워크 접속을 차단"):
            sock.connect_ex(("8.8.8.8", 443))
    finally:
        sock.close()
    assert expect_network_block == ["8.8.8.8:443", "8.8.8.8:443"]


def test_blocked_attempt_is_recorded_even_when_swallowed(expect_network_block: list[str]) -> None:
    """서비스 코드의 광범위한 except Exception이 차단 예외를 삼켜도 기록은 남는다.

    기록이 남으면 conftest의 autouse 픽스처가 이 픽스처를 쓰지 않는 테스트를 종료 시 실패시킨다.
    """
    try:
        socket.getaddrinfo("generativelanguage.googleapis.com", 443)
    except Exception:  # noqa: BLE001  서비스의 광범위한 예외 처리를 흉내 낸다
        pass
    assert expect_network_block == ["generativelanguage.googleapis.com:443"]


def test_opensearch_is_blocked_even_on_loopback(expect_network_block: list[str]) -> None:
    """CI의 OpenSearch 주소는 localhost:9200이다. 루프백이어도 막아야 로컬과 CI가 같게 드러난다."""
    parts = urlsplit(get_settings().OPENSEARCH_URL)
    port = parts.port or 9200
    with pytest.raises(RuntimeError, match="외부 네트워크 접속을 차단"):
        socket.getaddrinfo(parts.hostname, port)
    assert expect_network_block == [f"{parts.hostname}:{port}"]


def test_loopback_is_allowed() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        # 닫힌 포트라 연결은 거부되지만, 격리 장치가 막지 않고 운영체제 오류 코드가 돌아와야 한다
        assert isinstance(sock.connect_ex(("127.0.0.1", 9)), int)
    finally:
        sock.close()
