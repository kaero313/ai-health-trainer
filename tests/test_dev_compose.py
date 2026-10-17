"""개발용 docker-compose.yml의 호스트 포트가 이 PC 안(127.0.0.1)에서만 열리는지 검사한다.

DB·Redis는 기본 계정이거나 인증이 없고 OpenSearch는 보안 플러그인을 끈다. 모든 인터페이스에 열면
같은 네트워크의 다른 기기가 접속할 수 있다. 에뮬레이터(10.0.2.2)와 실기기(adb reverse)는
호스트의 127.0.0.1로 들어오므로 loopback 바인딩으로 충분하다.
CI harness-check 잡은 pytest만 설치하므로 YAML 라이브러리 없이 ports 목록만 읽는다.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"


def _port_mappings(text: str) -> dict[str, list[str]]:
    """{서비스: [포트 매핑 문자열]}. 서비스 바로 아래 `ports:` 목록의 `- "..."` 항목만 읽는다."""
    mappings: dict[str, list[str]] = {}
    service: str | None = None
    in_ports = False
    ports_indent = 0
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 2 and re.fullmatch(r"\s{2}[\w.-]+:\s*", line):
            service = line.strip().rstrip(":")
            in_ports = False
            continue
        if indent == 0:
            service = None
            in_ports = False
            continue
        if service and line.strip() == "ports:":
            in_ports = True
            ports_indent = indent
            continue
        if in_ports:
            if indent > ports_indent and line.strip().startswith("- "):
                mappings.setdefault(service, []).append(line.strip()[2:].strip().strip("\"'"))
            else:
                in_ports = False
    return mappings


def test_parser_reads_service_port_lists() -> None:
    text = 'services:\n  db:\n    ports:\n      - "5432:5432"\n    volumes:\n      - x:/y\n  api:\n    ports:\n      - 8000:8000\n'
    assert _port_mappings(text) == {"db": ["5432:5432"], "api": ["8000:8000"]}


def test_dev_compose_publishes_ports_on_loopback_only() -> None:
    mappings = _port_mappings(COMPOSE.read_text(encoding="utf-8"))
    # 백엔드·DB·Redis·OpenSearch가 모두 호스트 포트를 연다. 목록이 비면 파서가 깨진 것이다
    assert {"db", "redis", "opensearch", "backend"} <= set(mappings), mappings
    exposed = {
        service: port
        for service, ports in mappings.items()
        for port in ports
        if not port.startswith("127.0.0.1:")
    }
    assert not exposed, f"127.0.0.1에 묶지 않은 포트: {exposed}"
