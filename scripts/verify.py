"""프로젝트 검증 게이트와 실행 증거 기록.

순서(첫 실패에서 중단):
  1. render_check     scripts/harness.py render --check       (로컬 python, 역할 파일·스킬 사본 drift)
  2. harness_tests    pytest tests/                             (로컬 python, 하네스 자체 회귀)
  3. docker_ready     docker compose ps backend                 (backend 컨테이너가 떠 있는지)
  4. backend_ruff     docker compose exec backend python -m ruff check .
  5. backend_import   docker compose exec backend python -c "import app.main"
                                                                (pytest가 못 잡는 앱 진입점 오류 방지)
  6. alembic_heads    docker compose exec backend alembic heads (head가 하나인지)
  7. backend_pytest   docker compose exec backend pytest tests/ --junitxml
                                                                (JUnit은 docker compose cp로 회수)
  8. flutter_analyze  flutter analyze                           (--frontend 지정 또는 HEAD 대비 frontend/ 변경 시)
  9. flutter_test     flutter test --file-reporter json:...     (위와 같음)

    python scripts/verify.py                 # 전체
    python scripts/verify.py --fast          # 1·3·4·5·6만
    python scripts/verify.py --frontend      # 8·9 강제
    python scripts/verify.py --frontend-only # 1·8·9만 (Docker 없이)

백엔드 검증은 docker compose의 backend 컨테이너 안에서 돈다(`docker compose up -d` 선행).
flutter는 PATH에서 찾고, 없으면 FLUTTER_ROOT/bin/flutter를 쓴다.
결과는 .harness/runs/<id>/의 result.json·harness-junit.xml·junit.xml·flutter-tests.json에 남기고
마지막 줄에 요약을 출력한다. 테스트 명령이 성공해도 결과 파일이 없거나, 0건이거나, 실패·오류가
기록돼 있으면 실패로 처리한다. 실행 전후의 워킹트리 해시가 다르면 증거가 어느 상태를 말하는지
알 수 없으므로 실패(workspace_mutated)로 기록한다. 로컬 하위 명령은 이 스크립트를 실행한
인터프리터(sys.executable)로 돌린다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
RUNS_DIR = ROOT / ".harness" / "runs"
TAIL = 4000
SNAPSHOT_EXCLUDE_FILES = {".env", ".env.prod", ".env.local", "backend/.env"}
SNAPSHOT_EXCLUDE_PREFIXES = (".harness/", "logs/", "tmp_", "frontend/build/", "frontend/.dart_tool/")
PYTEST_SUMMARY = re.compile(r"(\d+) (passed|failed|skipped|deselected|errors?|xfailed|xpassed)")
CHILD_ENV = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "PYTEST_ADDOPTS": ""}
COMPOSE = ("docker", "compose")
BACKEND_SERVICE = "backend"
CONTAINER_JUNIT = "/tmp/harness-junit.xml"
# 컨테이너 안에서 보는 주소. 호스트 환경변수 TEST_DATABASE_URL과 섞이지 않도록 VERIFY_ 접두어로 덮어쓴다.
TEST_DATABASE_URL = os.environ.get(
    "VERIFY_TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@db:5432/health_trainer_test",
)
TEST_GEMINI_API_KEY = "dummy-key-for-test"
TEST_DATABASE_ADMIN_URL = os.environ.get(
    "VERIFY_TEST_DATABASE_ADMIN_URL",
    "postgresql+asyncpg://postgres:postgres@db:5432/postgres",
)


@dataclass
class Step:
    name: str
    command: list[str]
    cwd: Path
    check: Callable[[dict], str | None] | None = None  # 명령 성공 뒤 추가 판정. 사유를 돌려주면 실패
    after: Callable[[dict], None] | None = None  # 결과 파일 회수 등 후처리


def run(command: list[str], cwd: Path) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=1800, env={**os.environ, **CHILD_ENV},
        )
        code, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout or b""
        out = partial.decode("utf-8", "replace") if isinstance(partial, bytes) else partial
        code, err = 124, "timeout 1800s"
    except FileNotFoundError as exc:
        code, out, err = 127, "", str(exc)
    return {
        "command": command,
        "cwd": cwd.relative_to(ROOT).as_posix() if cwd != ROOT else ".",
        "exit_code": code,
        "seconds": round(time.monotonic() - started, 1),
        "stdout_tail": out[-TAIL:],
        "stderr_tail": err[-TAIL:],
    }


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return proc.stdout if proc.returncode == 0 else ""


def workspace_sha256() -> str:
    """추적+미추적(ignore 제외) 파일 내용 해시. 증거가 어느 트리 상태를 말하는지 고정한다."""
    listing = git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    lines = []
    for rel in sorted({p for p in listing.split("\0") if p}):
        if rel in SNAPSHOT_EXCLUDE_FILES or rel.startswith(SNAPSHOT_EXCLUDE_PREFIXES):
            continue
        path = ROOT / rel
        if path.is_file():
            lines.append(f"{rel} {hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def frontend_changed() -> bool:
    changed = git("diff", "--name-only", "HEAD", "--", "frontend/")
    untracked = git("ls-files", "--others", "--exclude-standard", "--", "frontend/")
    return bool(changed.strip() or untracked.strip())


def flutter_command() -> list[str]:
    """PATH의 flutter, 없으면 FLUTTER_ROOT(또는 FLUTTER_HOME)/bin/flutter."""
    found = shutil.which("flutter")
    if found:
        return [found]
    root = os.environ.get("FLUTTER_ROOT") or os.environ.get("FLUTTER_HOME")
    if root:
        candidate = Path(root) / "bin" / ("flutter.bat" if os.name == "nt" else "flutter")
        if candidate.is_file():
            return [str(candidate)]
    return ["flutter"]  # 없으면 실행 단계에서 exit 127로 기록된다


def pytest_summary(output: str) -> dict[str, int]:
    """pytest -q 마지막 요약 줄을 {결과: 건수}로 바꾼다."""
    for line in reversed(output.strip().splitlines()):
        found = PYTEST_SUMMARY.findall(line)
        if found and " in " in line:
            return {("error" if key.startswith("error") else key): int(n) for n, key in found}
    return {}


def junit_summary(path: Path) -> dict[str, int]:
    """JUnit XML의 testsuite 속성을 합산한다. 파일이 없거나 깨졌으면 빈 dict."""
    if not path.is_file():
        return {}
    try:
        suites = list(ET.parse(path).iter("testsuite"))
    except ET.ParseError:
        return {}
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.get(key, 0))
    return totals


def flutter_summary(path: Path) -> dict[str, int]:
    """flutter test --file-reporter json 결과(줄 단위 JSON 이벤트)를 JUnit과 같은 꼴로 합산한다.

    hidden 테스트(파일 로딩 등)는 세지 않는다. 마지막 done 이벤트가 없으면 증거로 보지 않는다.
    """
    if not path.is_file():
        return {}
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    finished = False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "testDone":
            if event.get("hidden"):
                continue
            totals["tests"] += 1
            if event.get("skipped"):
                totals["skipped"] += 1
            result = event.get("result")
            if result == "failure":
                totals["failures"] += 1
            elif result == "error":
                totals["errors"] += 1
        elif kind == "done":
            finished = True
    return totals if finished else {}


def evidence_paths(report_dir: Path) -> dict[str, Path]:
    """결과 파일을 남기는 단계와 그 파일 경로."""
    return {
        "harness_tests": report_dir / "harness-junit.xml",
        "backend_pytest": report_dir / "junit.xml",
        "flutter_test": report_dir / "flutter-tests.json",
    }


def evidence_summary(step_name: str, path: Path) -> dict[str, int]:
    if step_name == "flutter_test":
        return flutter_summary(path)
    return junit_summary(path)


def container_running(result: dict) -> str | None:
    """docker compose ps -q 출력이 비어 있으면 backend 컨테이너가 없다."""
    if result["stdout_tail"].strip():
        return None
    return "backend_container_not_running"


def single_head(result: dict) -> str | None:
    """alembic heads 출력에 (head)가 정확히 하나여야 한다."""
    heads = [line for line in result["stdout_tail"].splitlines() if "(head)" in line]
    if len(heads) == 1:
        return None
    return f"alembic_heads_{len(heads)}"


def build_steps(fast: bool, frontend: bool, frontend_only: bool, report_dir: Path) -> list[Step]:
    py = sys.executable
    evidence = evidence_paths(report_dir)
    steps = [Step("render_check", [py, "scripts/harness.py", "render", "--check"], ROOT)]
    if not fast and not frontend_only:
        steps.append(Step(
            "harness_tests",
            [py, "-m", "pytest", "tests", "-q", f"--junitxml={evidence['harness_tests']}"],
            ROOT,
        ))
    if not frontend_only:
        exec_backend = [*COMPOSE, "exec", "-T", BACKEND_SERVICE]
        steps += [
            Step(
                "docker_ready",
                [*COMPOSE, "ps", "--status", "running", "-q", BACKEND_SERVICE],
                ROOT,
                check=container_running,
            ),
            Step("backend_ruff", [*exec_backend, "python", "-m", "ruff", "check", "."], ROOT),
            Step("backend_import", [*exec_backend, "python", "-c", "import app.main"], ROOT),
            Step("alembic_heads", [*exec_backend, "alembic", "heads"], ROOT, check=single_head),
        ]
        if not fast:
            def collect_junit(result: dict) -> None:
                copied = run(
                    [*COMPOSE, "cp", f"{BACKEND_SERVICE}:{CONTAINER_JUNIT}", str(evidence["backend_pytest"])],
                    ROOT,
                )
                result["junit_copy_exit_code"] = copied["exit_code"]

            steps.append(Step(
                "backend_pytest",
                [
                    *COMPOSE, "exec", "-T",
                    "-e", f"TEST_DATABASE_URL={TEST_DATABASE_URL}",
                    "-e", f"TEST_DATABASE_ADMIN_URL={TEST_DATABASE_ADMIN_URL}",
                    # 컨테이너는 backend/.env의 실제 키를 받는다. CI와 같은 가짜 키로 테스트한다.
                    "-e", f"GEMINI_API_KEY={TEST_GEMINI_API_KEY}",
                    BACKEND_SERVICE,
                    "pytest", "tests/", "-q", "--tb=short", "-p", "no:cacheprovider",
                    f"--junitxml={CONTAINER_JUNIT}",
                ],
                ROOT,
                after=collect_junit,
            ))
    if frontend:
        flutter = flutter_command()
        steps += [
            Step("flutter_analyze", [*flutter, "analyze"], FRONTEND),
            Step(
                "flutter_test",
                [*flutter, "test", "--file-reporter", f"json:{evidence['flutter_test'].as_posix()}"],
                FRONTEND,
            ),
        ]
    return steps


def evidence_error(step: dict) -> str | None:
    """명령은 성공했지만 테스트 증거가 통과로 볼 수 없는 경우의 사유."""
    junit = step.get("junit")
    if junit is None or step["exit_code"] != 0:
        return None
    if not junit:
        return "junit_missing"
    if junit["tests"] == 0:
        return "zero_tests"
    if junit["failures"] or junit["errors"]:
        return "junit_unsuccessful"
    return None


def describe(step: dict) -> str:
    name = step["step"]
    if step["exit_code"] != 0:
        return f"{name} FAIL(exit {step['exit_code']})"
    if step.get("evidence_error"):
        return f"{name} FAIL({step['evidence_error']})"
    if step.get("check_error"):
        return f"{name} FAIL({step['check_error']})"
    if name == "backend_pytest":
        summary = step.get("summary") or {}
        parts = [f"{n} {key}" for key, n in summary.items()] or ["요약 없음"]
        return "backend_pytest " + ", ".join(parts)
    if name in {"flutter_test", "harness_tests"} and step.get("junit"):
        junit = step["junit"]
        return f"{name} {junit['tests']} tests, {junit['skipped']} skipped"
    return f"{name} OK"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="프로젝트 검증 게이트")
    parser.add_argument("--fast", action="store_true", help="render 검사·ruff·기동·alembic heads만")
    parser.add_argument("--frontend", action="store_true", help="flutter analyze/test 강제")
    parser.add_argument("--frontend-only", action="store_true", help="Docker 없이 render 검사와 flutter만")
    args = parser.parse_args(argv)

    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    report_dir = RUNS_DIR / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    evidence = evidence_paths(report_dir)
    run_frontend = args.frontend or args.frontend_only or (not args.fast and frontend_changed())
    steps = build_steps(args.fast, run_frontend, args.frontend_only, report_dir)
    before = workspace_sha256()
    results: list[dict] = []
    failed_step: str | None = None
    for step in steps:
        result = run(step.command, step.cwd)
        result["step"] = step.name
        if step.after is not None:
            step.after(result)
        if step.name == "backend_pytest":
            result["summary"] = pytest_summary(result["stdout_tail"])
        if step.name in evidence:
            result["junit"] = evidence_summary(step.name, evidence[step.name])
            result["evidence_error"] = evidence_error(result)
        if result["exit_code"] == 0 and not result.get("evidence_error") and step.check is not None:
            result["check_error"] = step.check(result)
        results.append(result)
        if result["exit_code"] != 0 or result.get("evidence_error") or result.get("check_error"):
            failed_step = step.name
            break
    after = workspace_sha256()
    reason = failed_step or "passed"
    if failed_step is None and before != after:
        reason = "workspace_mutated"

    report = {
        "run_id": run_id,
        "status": "passed" if reason == "passed" else "failed",
        "reason": reason,
        "failed_step": failed_step,
        "exit_code": 0 if reason == "passed" else 1,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "base_commit": git("rev-parse", "HEAD").strip(),
        "workspace_sha256": before,
        "workspace_sha256_after": after,
        "python": sys.version.split()[0],
        "interpreter": sys.executable,
        "backend_service": BACKEND_SERVICE,
        "flutter": flutter_command()[0] if run_frontend else None,
        "frontend": run_frontend,
        "frontend_only": args.frontend_only,
        "fast": args.fast,
        "evidence_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in evidence.items()
            if path.is_file()
        },
        "steps": results,
    }
    report_path = report_dir / "result.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    if failed_step is not None:
        failed = results[-1]
        sys.stderr.write((failed["stdout_tail"] + failed["stderr_tail"]).rstrip() + "\n")
    summary = " | ".join(describe(step) for step in results)
    if reason == "workspace_mutated":
        summary += " | 실행 중 워킹트리 변경됨"
    print(f"verify: {report['status']} | {summary} | report {report_path.relative_to(ROOT).as_posix()}")
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
