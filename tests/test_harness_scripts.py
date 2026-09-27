"""하네스 스크립트(scripts/harness.py, scripts/verify.py) 자체 회귀.

로컬 python(3.11+)과 pytest만 있으면 돈다. 백엔드 의존성이나 Docker는 필요 없다.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROLES = {"scout", "backend", "frontend", "qa", "reviewer"}
SKILL_MIRROR_PREFIX = ".agents/skills/"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"harness_scripts_{name}", ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # dataclass 데코레이터가 sys.modules에서 모듈을 찾으므로 실행 전에 등록한다
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


harness = _load("harness")
verify = _load("verify")


def _role_outputs(outputs: dict[str, str]) -> dict[str, str]:
    return {rel: text for rel, text in outputs.items() if not rel.startswith(SKILL_MIRROR_PREFIX)}


def test_generated_role_files_have_frontmatter_and_tool_policy() -> None:
    outputs = _role_outputs(harness.generated())
    claude = {f".claude/agents/{role}.md" for role in ROLES}
    codex = {f".codex/agents/{role}.toml" for role in ROLES}
    assert set(outputs) == claude | codex | {".codex/config.toml"}
    for rel in sorted(claude):
        text = outputs[rel]
        role = rel.rsplit("/", 1)[1].removesuffix(".md")
        head = text.split("---", 2)[1]
        assert f"\nname: {role}\n" in head
        assert "\nmodel: claude-" in head and "\neffort: " in head
        assert harness.MARKER in text
        tools = next(line for line in head.splitlines() if line.startswith("tools: "))
        listed = tools.removeprefix("tools: ").split(", ")
        # 모든 역할이 스킬을 부르고 GitNexus 그래프를 읽을 수 있어야 한다
        assert "Skill" in listed, role
        assert set(harness.GITNEXUS_READ_TOOLS) <= set(listed), role
        if role in {"scout", "reviewer"}:
            assert listed == list(harness.READ_ONLY_TOOLS)
            assert not {"Edit", "Write", "Bash"} & set(listed)
        else:
            assert tools.endswith("Edit, Write, Bash")


def test_gitnexus_role_tools_match_settings_allow_list() -> None:
    """역할에 주는 GitNexus 도구는 권한 설정에서 승인 없이 허용한 읽기 전용 도구와 같아야 한다."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    allowed = {p for p in settings["permissions"]["allow"] if p.startswith("mcp__gitnexus__")}
    assert set(harness.GITNEXUS_READ_TOOLS) == allowed


def test_role_bodies_direct_existing_skills() -> None:
    """역할 본문은 Skill 도구로 쓸 스킬을 지시하고, 가리키는 스킬 이름은 실제로 있어야 한다."""
    import re

    skills = {path.parent.name for path in harness.SKILLS_DIR.glob("*/SKILL.md")}
    for role in ROLES:
        body = (ROOT / "harness" / "roles" / f"{role}.md").read_text(encoding="utf-8")
        assert "Skill 도구로 불러서 따른다" in body, role
        referenced = set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", body))
        assert referenced, f"{role}: 지시하는 스킬이 없다"
        assert referenced <= skills, f"{role}: 없는 스킬 이름 {sorted(referenced - skills)}"


def test_skill_mirror_copies_every_claude_skill_file() -> None:
    outputs = harness.generated()
    mirror = {rel for rel in outputs if rel.startswith(SKILL_MIRROR_PREFIX)}
    sources = {
        f"{SKILL_MIRROR_PREFIX}{path.relative_to(harness.SKILLS_DIR).as_posix()}"
        for path in harness.SKILLS_DIR.rglob("*")
        if path.is_file()
    }
    assert mirror == sources and mirror, "스킬 사본은 .claude/skills의 모든 파일을 담아야 한다"
    assert any(rel.endswith("/SKILL.md") for rel in mirror)
    for rel in mirror:
        source = harness.SKILLS_DIR / rel.removeprefix(SKILL_MIRROR_PREFIX)
        assert outputs[rel] == source.read_text(encoding="utf-8")


def test_committed_generated_files_match_sources(capsys: pytest.CaptureFixture[str]) -> None:
    assert harness.render(check=True) == 0
    assert "OK" in capsys.readouterr().out


@pytest.fixture
def harness_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for rel in ("AGENTS.md", "harness/agents.toml"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    shutil.copytree(ROOT / "harness" / "roles", tmp_path / "harness" / "roles")
    shutil.copytree(ROOT / ".claude" / "skills", tmp_path / ".claude" / "skills")
    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness, "CONFIG", tmp_path / "harness" / "agents.toml")
    monkeypatch.setattr(harness, "COMMON", tmp_path / "AGENTS.md")
    monkeypatch.setattr(harness, "ROLES_DIR", tmp_path / "harness" / "roles")
    monkeypatch.setattr(harness, "SKILLS_DIR", tmp_path / ".claude" / "skills")
    monkeypatch.setattr(harness, "OUTPUT_DIR", tmp_path / ".claude" / "agents")
    monkeypatch.setattr(harness, "CODEX_DIR", tmp_path / ".codex")
    monkeypatch.setattr(harness, "CODEX_SKILLS_DIR", tmp_path / ".agents" / "skills")
    monkeypatch.setattr(harness, "MCP_CONFIG", tmp_path / ".mcp.json")
    return tmp_path


def test_render_detects_missing_changed_and_stale_files(harness_copy: Path) -> None:
    agents = harness_copy / ".claude" / "agents"
    assert harness.render(check=True) == 1  # 생성물 없음
    assert harness.render(check=False) == 0
    assert harness.render(check=True) == 0
    role = harness_copy / "harness" / "roles" / "backend.md"
    role.write_text(role.read_text(encoding="utf-8") + "- 임시 규칙\n", encoding="utf-8")
    assert harness.render(check=True) == 1  # 원본 변경
    assert harness.render(check=False) == 0 and harness.render(check=True) == 0
    stale = agents / "ghost.md"
    stale.write_text(f"---\nname: ghost\n---\n<!-- {harness.MARKER} -->\n", encoding="utf-8")
    codex_stale = harness_copy / ".codex" / "agents" / "ghost.toml"
    codex_stale.write_text(f"# {harness.MARKER}\nname = \"ghost\"\n", encoding="utf-8")
    assert harness.render(check=True) == 1  # 원본 없는 생성물
    assert harness.render(check=False) == 0
    assert not stale.exists() and not codex_stale.exists()


def test_render_keeps_skill_mirror_in_sync(harness_copy: Path) -> None:
    assert harness.render(check=False) == 0
    mirror = harness_copy / ".agents" / "skills"
    assert (mirror / "verify-and-stop" / "SKILL.md").is_file()
    # 원본 스킬 수정 → drift
    skill = harness_copy / ".claude" / "skills" / "verify-and-stop" / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\n추가 줄\n", encoding="utf-8")
    assert harness.render(check=True) == 1
    assert harness.render(check=False) == 0 and harness.render(check=True) == 0
    assert (mirror / "verify-and-stop" / "SKILL.md").read_text(encoding="utf-8") == skill.read_text(
        encoding="utf-8"
    )
    # 원본이 사라진 스킬 사본은 지운다 (빈 디렉터리까지)
    ghost_dir = mirror / "ghost-skill"
    ghost_dir.mkdir()
    (ghost_dir / "SKILL.md").write_text("---\nname: ghost\n---\n", encoding="utf-8")
    assert harness.render(check=True) == 1
    assert harness.render(check=False) == 0
    assert not ghost_dir.exists()
    # 사본 자리에 파일(링크 텍스트)이 있으면 안내하고 멈춘다
    shutil.rmtree(mirror)
    mirror.write_text("../.claude/skills", encoding="utf-8")
    with pytest.raises(harness.HarnessError, match="심볼릭 링크"):
        harness.render(check=True)


def test_render_refuses_to_overwrite_unowned_file(harness_copy: Path) -> None:
    agents = harness_copy / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "scout.md").write_text("손으로 쓴 파일\n", encoding="utf-8")
    with pytest.raises(harness.HarnessError):
        harness.render(check=True)


def test_codex_config_includes_mcp_servers_only_when_mcp_json_exists(harness_copy: Path) -> None:
    codex = tomllib.loads(harness.generated()[".codex/config.toml"])
    assert "mcp_servers" not in codex
    (harness_copy / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"demo": {"command": "cmd", "args": ["/c", "demo"], "env": {"X": "1"}}}}),
        encoding="utf-8",
    )
    codex = tomllib.loads(harness.generated()[".codex/config.toml"])
    assert codex["mcp_servers"]["demo"] == {"command": "cmd", "args": ["/c", "demo"], "env": {"X": "1"}}
    (harness_copy / ".mcp.json").write_text(json.dumps({"mcpServers": {"bad": {"url": "http://x"}}}))
    with pytest.raises(harness.HarnessError, match="command"):
        harness.generated()


def test_pytest_summary_parses_last_summary_line() -> None:
    output = "....\n1 failed, 183 passed, 8 deselected, 2 errors in 30.81s\n"
    assert verify.pytest_summary(output) == {
        "failed": 1, "passed": 183, "deselected": 8, "error": 2,
    }
    assert verify.pytest_summary("no summary here") == {}


def test_junit_summary_sums_suites(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuites><testsuite tests="3" failures="1" errors="0" skipped="1"/>'
        '<testsuite tests="2" failures="0" errors="1" skipped="0"/></testsuites>',
        encoding="utf-8",
    )
    assert verify.junit_summary(junit) == {"tests": 5, "failures": 1, "errors": 1, "skipped": 1}
    assert verify.junit_summary(tmp_path / "missing.xml") == {}


def test_flutter_summary_counts_visible_tests_and_requires_done(tmp_path: Path) -> None:
    report = tmp_path / "flutter-tests.json"
    events = [
        {"type": "start", "protocolVersion": "0.1.1"},
        {"type": "testStart", "test": {"id": 1, "name": "loading test/a_test.dart"}},
        {"type": "testDone", "testID": 1, "result": "success", "hidden": True, "skipped": False},
        {"type": "testDone", "testID": 2, "result": "success", "hidden": False, "skipped": False},
        {"type": "testDone", "testID": 3, "result": "failure", "hidden": False, "skipped": False},
        {"type": "testDone", "testID": 4, "result": "error", "hidden": False, "skipped": False},
        {"type": "testDone", "testID": 5, "result": "success", "hidden": False, "skipped": True},
    ]
    report.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    assert verify.flutter_summary(report) == {}  # done 이벤트 없음
    report.write_text(
        report.read_text(encoding="utf-8") + json.dumps({"type": "done", "success": False}) + "\n",
        encoding="utf-8",
    )
    assert verify.flutter_summary(report) == {"tests": 4, "failures": 1, "errors": 1, "skipped": 1}
    assert verify.flutter_summary(tmp_path / "missing.json") == {}


def test_build_steps_respects_flags(tmp_path: Path) -> None:
    evidence = verify.evidence_paths(tmp_path)
    steps = verify.build_steps(fast=False, frontend=False, frontend_only=False, report_dir=tmp_path)
    names = [step.name for step in steps]
    assert names == [
        "render_check", "harness_tests", "docker_ready", "backend_ruff", "backend_import",
        "alembic_heads", "backend_pytest",
    ]
    by_name = {step.name: step for step in steps}
    assert f"--junitxml={verify.CONTAINER_JUNIT}" in by_name["backend_pytest"].command
    assert "GEMINI_API_KEY=dummy-key-for-test" in by_name["backend_pytest"].command
    assert by_name["backend_pytest"].after is not None
    assert by_name["docker_ready"].check is verify.container_running
    assert by_name["alembic_heads"].check is verify.single_head
    assert f"--junitxml={evidence['harness_tests']}" in by_name["harness_tests"].command

    steps = verify.build_steps(fast=True, frontend=True, frontend_only=False, report_dir=tmp_path)
    names = [step.name for step in steps]
    assert names == [
        "render_check", "docker_ready", "backend_ruff", "backend_import", "alembic_heads",
        "flutter_analyze", "flutter_test",
    ]
    flutter_test = dict((step.name, step.command) for step in steps)["flutter_test"]
    assert "--file-reporter" in flutter_test
    assert f"json:{evidence['flutter_test'].as_posix()}" in flutter_test

    steps = verify.build_steps(fast=False, frontend=True, frontend_only=True, report_dir=tmp_path)
    assert [step.name for step in steps] == ["render_check", "flutter_analyze", "flutter_test"]


def test_step_checks_detect_missing_container_and_multiple_heads() -> None:
    assert verify.container_running({"stdout_tail": "abc123\n"}) is None
    assert verify.container_running({"stdout_tail": "\n"}) == "backend_container_not_running"
    assert verify.single_head({"stdout_tail": "e7f8a9b0c113 (head)\n"}) is None
    assert verify.single_head({"stdout_tail": "a (head)\nb (head)\n"}) == "alembic_heads_2"
    assert verify.single_head({"stdout_tail": ""}) == "alembic_heads_0"


def test_evidence_error_rejects_missing_empty_and_failed_junit() -> None:
    ok = {"tests": 3, "failures": 0, "errors": 0, "skipped": 1}
    assert verify.evidence_error({"exit_code": 0, "junit": ok}) is None
    assert verify.evidence_error({"exit_code": 0, "junit": {}}) == "junit_missing"
    assert verify.evidence_error({"exit_code": 0, "junit": {**ok, "tests": 0}}) == "zero_tests"
    assert verify.evidence_error({"exit_code": 0, "junit": {**ok, "errors": 1}}) == (
        "junit_unsuccessful"
    )
    # 명령 자체가 실패했으면 exit code가 사유이므로 따로 적지 않는다
    assert verify.evidence_error({"exit_code": 1, "junit": {}}) is None
    # 결과 파일을 남기지 않는 단계는 검사하지 않는다
    assert verify.evidence_error({"exit_code": 0}) is None


def test_describe_marks_failures_and_counts() -> None:
    assert verify.describe({"step": "backend_ruff", "exit_code": 0}) == "backend_ruff OK"
    assert verify.describe({"step": "backend_ruff", "exit_code": 2}) == "backend_ruff FAIL(exit 2)"
    assert verify.describe(
        {"step": "backend_pytest", "exit_code": 0, "summary": {"passed": 3}}
    ) == "backend_pytest 3 passed"
    assert verify.describe(
        {"step": "flutter_test", "exit_code": 0, "evidence_error": "zero_tests"}
    ) == "flutter_test FAIL(zero_tests)"
    assert verify.describe(
        {"step": "alembic_heads", "exit_code": 0, "check_error": "alembic_heads_2"}
    ) == "alembic_heads FAIL(alembic_heads_2)"
    assert verify.describe({
        "step": "flutter_test", "exit_code": 0,
        "junit": {"tests": 39, "failures": 0, "errors": 0, "skipped": 0},
    }) == "flutter_test 39 tests, 0 skipped"


def test_role_files_point_to_agents_md_instead_of_copying_it(harness_copy: Path) -> None:
    outputs = _role_outputs(harness.generated())
    agents_md = (harness_copy / "AGENTS.md").read_text(encoding="utf-8")
    first_rule_line = next(
        line for line in agents_md.splitlines() if line.startswith("- ") and len(line) > 40
    )
    for rel, text in outputs.items():
        assert first_rule_line not in text
        if rel.startswith(".claude/agents/"):
            assert harness.COMMON_POINTER in text
        elif rel.startswith(".codex/agents/"):
            instructions = tomllib.loads(text)["developer_instructions"]
            assert instructions.startswith(harness.CODEX_POINTER)
    # AGENTS.md를 고쳐도 역할 파일은 바뀌지 않는다
    assert harness.render(check=False) == 0
    (harness_copy / "AGENTS.md").write_text(agents_md + "- 임시 규칙\n", encoding="utf-8")
    assert harness.render(check=True) == 0
    # 원본이 없으면 안내가 가리킬 곳이 없으므로 실패한다
    (harness_copy / "AGENTS.md").unlink()
    with pytest.raises(harness.HarnessError):
        harness.generated()


@pytest.mark.parametrize(
    "line", ['"claude-fable-5-1" = "Fable 5.1"\n', '"gpt-5.6-terra" = "GPT-5.6 Terra"\n']
)
def test_missing_display_name_is_rejected(harness_copy: Path, line: str) -> None:
    config = harness_copy / "harness" / "agents.toml"
    text = config.read_text(encoding="utf-8")
    assert line in text
    config.write_text(text.replace(line, ""), encoding="utf-8")
    with pytest.raises(harness.HarnessError, match=line.split('"')[1]):
        harness.generated()


def test_codex_files_match_agents_toml() -> None:
    config = _config()
    outputs = harness.generated()
    for name, role in config["roles"].items():
        text = outputs[f".codex/agents/{name}.toml"]
        assert text.startswith(f"# {harness.MARKER}")
        agent = tomllib.loads(text)
        assert agent["name"] == name and agent["description"] == role["description"]
        assert (agent["model"], agent["model_reasoning_effort"]) == (role["codex_model"], role["effort"])
        assert agent["sandbox_mode"] == ("read-only" if role["read_only"] else "workspace-write")
    codex = tomllib.loads(outputs[".codex/config.toml"])
    lead = config["lead"]
    assert (codex["model"], codex["model_reasoning_effort"]) == (lead["codex_model"], lead["effort"])
    assert codex["approval_policy"] == "on-request"
    assert codex["sandbox_workspace_write"]["network_access"] is False
    assert codex["agents"]["max_concurrent_threads_per_session"] == harness.CODEX_MAX_THREADS


def test_codex_config_mcp_servers_match_committed_mcp_json() -> None:
    codex = tomllib.loads(harness.generated()[".codex/config.toml"])
    servers = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    assert set(codex["mcp_servers"]) == set(servers)
    for name, server in servers.items():
        converted = codex["mcp_servers"][name]
        assert (converted["command"], converted["args"]) == (server["command"], server["args"])
        assert converted.get("env", {}) == server.get("env", {})


def test_gitnexus_setup_keeps_rule_files_and_skill_mirror_untouched() -> None:
    """analyze가 AGENTS.md·CLAUDE.md에 블록을 넣거나 .agents/skills에 스킬을 쓰면 하네스 원본이 깨진다."""
    rc = json.loads((ROOT / ".gitnexusrc").read_text(encoding="utf-8"))["analyze"]
    assert rc["skipAgentsMd"] is True and rc["skipSkills"] is True and rc["noStats"] is True
    for rule_file in ("AGENTS.md", "CLAUDE.md"):
        assert "gitnexus:start" not in (ROOT / rule_file).read_text(encoding="utf-8"), rule_file
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    servers = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    assert set(settings["enabledMcpjsonServers"]) == set(servers)
    # 쓰기 도구(rename 등)는 allow에 두지 않는다
    mcp_allowed = [p for p in settings["permissions"]["allow"] if p.startswith("mcp__gitnexus__")]
    assert mcp_allowed and not any(p.endswith(("__rename", "__cypher")) for p in mcp_allowed)
    assert ".gitnexus/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_claude_lead_settings_match_agents_toml() -> None:
    lead = _config()["lead"]
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert (settings["model"], settings["effortLevel"]) == (lead["claude_model"], lead["effort"])


def test_claude_settings_block_env_files_and_gate_destructive_git() -> None:
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    permissions = settings["permissions"]
    for env_file in (".env", ".env.prod", "backend/.env"):
        assert f"Read(./{env_file})" in permissions["deny"], env_file
    for command in ("git push", "git reset --hard"):
        assert f"Bash({command})" in permissions["ask"] and f"Bash({command} *)" in permissions["ask"]


def test_codex_skill_directory_mirrors_claude_skills() -> None:
    mirror = ROOT / ".agents" / "skills"
    assert mirror.is_dir(), ".agents/skills는 .claude/skills의 사본 디렉터리여야 한다 (render가 만든다)"
    source_files = {
        path.relative_to(harness.SKILLS_DIR).as_posix()
        for path in harness.SKILLS_DIR.rglob("*")
        if path.is_file()
    }
    mirror_files = {path.relative_to(mirror).as_posix() for path in mirror.rglob("*") if path.is_file()}
    assert mirror_files == source_files


def _table_rows(path: Path, first_header: str) -> dict[str, list[str]]:
    """첫 머리칸이 first_header인 마크다운 표를 {역할: 나머지 칸}으로 읽는다.

    머리줄은 표의 첫 줄만 인정한다. 다른 표의 본문 행이 우연히 같은 단어로 시작해도 잡지 않는다.
    """
    rows: dict[str, list[str]] = {}
    in_table = False
    previous_was_table_line = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            if in_table:
                break
            previous_was_table_line = False
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        is_first_line = not previous_was_table_line
        previous_was_table_line = True
        if not in_table and is_first_line and cells[0] == first_header:
            in_table = True
            continue
        if in_table and not set(cells[0]) <= {"-", ":"}:
            rows[cells[0]] = cells[1:]
    return rows


def _config() -> dict:
    return tomllib.loads((ROOT / "harness" / "agents.toml").read_text(encoding="utf-8"))


def _expected_roles() -> tuple[dict, dict]:
    config = _config()
    return config["roles"], config["display"]["models"]


def _paths_cell(role: dict) -> str:
    return " ".join(f"`{p}`" for p in role["allowed_paths"]) or "없음"


def _model_pair(role: dict, names: dict) -> str:
    return f"{names[role['claude_model']]} / {names[role['codex_model']]}"


def test_agents_md_role_table_matches_agents_toml() -> None:
    roles, names = _expected_roles()
    rows = _table_rows(ROOT / "AGENTS.md", "역할")
    assert set(rows) == set(roles), "AGENTS.md 역할 표와 agents.toml 역할이 다르다"
    for name, role in roles.items():
        models, effort, paths = rows[name][0], rows[name][1], rows[name][2]
        assert models == _model_pair(role, names), name
        assert effort == role["effort"], name
        assert paths == _paths_cell(role), name


def test_readme_role_table_matches_agents_toml() -> None:
    roles, names = _expected_roles()
    rows = _table_rows(ROOT / "README.md", "역할")
    lead = rows.pop("lead")
    assert lead[:2] == [_model_pair(_config()["lead"], names), _config()["lead"]["effort"]], "lead 행"
    assert set(rows) == set(roles), "README 역할 표와 agents.toml 역할이 다르다"
    for name, role in roles.items():
        models, effort, permission = rows[name][0], rows[name][1], rows[name][2]
        assert models == _model_pair(role, names), name
        assert effort == role["effort"], name
        assert permission == ("읽기 전용" if role["read_only"] else "쓰기"), name


def test_workflow_doc_role_table_matches_agents_toml() -> None:
    roles, _ = _expected_roles()
    rows = _table_rows(ROOT / "docs" / "DEVELOPMENT_WORKFLOW.md", "역할")
    assert set(rows) == set(roles), "DEVELOPMENT_WORKFLOW.md 역할 표와 agents.toml 역할이 다르다"
    for name, role in roles.items():
        claude, codex, effort, paths, tools = rows[name][:5]
        assert (claude, codex, effort) == (role["claude_model"], role["codex_model"], role["effort"])
        assert paths == _paths_cell(role), name
        expected_tools = "Read, Glob, Grep, Skill, GitNexus 읽기" if role["read_only"] else "+ Edit, Write, Bash"
        assert tools == expected_tools, name
