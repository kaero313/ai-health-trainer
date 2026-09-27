# AI Health Trainer 개발 워크플로우

Claude Code와 Codex로 개발할 때 쓰는 하네스의 사용법이다. 공통 규칙은 [AGENTS.md](../AGENTS.md)에 있고, 이 문서는 파일 구성·역할·검증·커밋 절차만 다룬다. ai-trade-manager의 하네스 1.0을 이 프로젝트 구조(backend는 Docker 컨테이너, frontend는 Flutter)에 맞게 옮겼다.

## 1. 파일 구성

| 경로 | 역할 | 추적 |
|---|---|---|
| `AGENTS.md` | 공통 규칙 원본. `CLAUDE.md`가 `@AGENTS.md`로 불러오고 Codex는 직접 읽는다 | O |
| `CLAUDE.md` | Claude Code 진입점 | O |
| `.claude/settings.json` | lead 모델·effort와 권한. `.env` 계열 Read 차단, `git push`·`git reset --hard`는 확인, 검증 명령은 allow | O |
| `.claude/settings.local.json` | 개인 설정(예: `FLUTTER_ROOT`). `.gitignore`로 제외 | X |
| `harness/agents.toml`, `harness/roles/*.md` | 역할·모델·effort·허용 경로와 역할 본문의 원본. lead 모델은 `[lead]` | O |
| `.claude/agents/*.md` | `scripts/harness.py render` 생성물(Claude Code 역할). 직접 편집 금지 | O |
| `.codex/agents/*.toml`, `.codex/config.toml` | `scripts/harness.py render` 생성물(Codex 역할, lead 모델·승인·샌드박스). 직접 편집 금지 | O |
| `.claude/skills/*/SKILL.md` | 절차 스킬 5종과 GitNexus 스킬 6종. 제3자 출처는 `.claude/skills/NOTICE.md` | O |
| `.agents/skills/**` | `scripts/harness.py render`가 만드는 `.claude/skills` 사본. Codex가 같은 스킬을 읽는다. 직접 편집 금지 | O |
| `.gitnexusrc`, `.mcp.json` | GitNexus 인덱싱 기본값, MCP 서버 설정(render가 Codex 설정으로도 옮긴다) | O |
| `.gitnexus/` | GitNexus 인덱스. 약 100MB | X |
| `scripts/harness.py` | 역할 파일·스킬 사본 생성기 | O |
| `scripts/verify.py` | 검증 게이트와 증거 기록 | O |
| `pytest.ini`, `tests/test_harness_scripts.py` | 루트 pytest는 하네스 자체 테스트만 돈다 | O |
| `backend/pytest.ini`, `backend/tests/conftest.py` | 백엔드 테스트 설정(`--strict-markers`, `migration` 마커)과 테스트 격리 | O |
| `backend/ruff.toml` | ruff 규칙 고정(E4·E7·E9·F) | O |
| `.gitattributes` | 텍스트 파일 LF 고정, 바이너리 지정 | O |
| `.github/workflows/ci.yml` | CI 세 잡 | O |
| `.harness/runs/<id>/result.json` | 검증 증거 | X |

## 2. 역할과 모델

| 역할 | Claude 모델 | Codex 모델 | effort | 쓰기 허용 | Claude 도구 |
|---|---|---|---|---|---|
| scout | claude-sonnet-5 | gpt-6-luna | low | 없음 | Read, Glob, Grep, Skill, GitNexus 읽기 |
| backend | claude-opus-5-5 | gpt-5.6-terra | high | `backend/` `docs/` | + Edit, Write, Bash |
| frontend | claude-opus-5-5 | gpt-5.6-terra | high | `frontend/` `docs/` | + Edit, Write, Bash |
| qa | claude-opus-5-5 | gpt-6-sol | high | `backend/tests/` `frontend/test/` | + Edit, Write, Bash |
| reviewer | claude-fable-5-1 | gpt-6-sol | xhigh | 없음 | Read, Glob, Grep, Skill, GitNexus 읽기 |

lead는 대화형 세션 자신이고, 모델은 `agents.toml`의 `[lead]`(claude-opus-5-5 / gpt-6-sol, xhigh)다. Codex는 render가 이 값으로 `.codex/config.toml`을 만들고, Claude Code는 권한 설정과 한 파일인 `.claude/settings.json`의 `model`·`effortLevel`을 손으로 맞춘다. 두 값이 `[lead]`와 어긋나면 테스트가 실패한다. 역할을 바꾸려면 `harness/agents.toml`이나 `harness/roles/<role>.md`를 고치고 render를 돌린다. 이 표와 `AGENTS.md` §8, `README.md` "개발 하네스" 표는 `tests/test_harness_scripts.py`가 `agents.toml`과 대조하므로, 모델·effort·쓰기 경로를 바꾸면 네 곳을 함께 고쳐야 테스트가 통과한다. 새 모델을 쓰면 `agents.toml`의 `[display.models]`에 표기명도 추가한다.

역할 파일에는 `AGENTS.md` 전문을 복사하지 않고 "먼저 읽는다"는 안내만 넣는다. Claude Code는 `CLAUDE.md`로, Codex는 저장소 루트 지시 파일로 `AGENTS.md`를 이미 불러오기 때문이다. 역할 해시도 역할 원본만으로 계산하므로 `AGENTS.md`만 고쳤을 때는 render가 필요 없다. 서브에이전트에 주입되는 `AGENTS.md`는 세션 시작 시점의 사본이므로(ai-trade-manager 실측), 고친 뒤 서브에이전트에 반영하려면 새 세션을 연다.

```sh
python scripts/harness.py render          # 생성·갱신
python scripts/harness.py render --check  # drift 검사. verify.py가 매번 실행한다
```

**모델을 바꾸면 실제 실행으로 확인한다.** 설정 파일 검사로는 잘못된 모델 ID를 잡지 못한다. 존재하지 않는 ID는 실행 시점에야 실패한다. 바꾼 역할마다 도구 없이 한 번 실행해, 실행 기록의 모델명이 설정과 같은지 본다. lead는 `--agent` 없이 실행한다.

```sh
claude -p --agent <역할> --output-format stream-json --verbose --no-session-persistence \
  --max-turns 1 --tools "" --strict-mcp-config "Reply with exactly: MODEL_OK"
# system/init의 model과 result의 modelUsage 키가 설정한 모델 ID와 같아야 한다
```

2026-09-25 도입 시 여섯 역할 모두 실제 실행으로 확인했다. scout는 `claude-sonnet-5`, backend·frontend·qa는 `claude-opus-5-5`, reviewer와 lead는 `claude-fable-5-1`로 실행됐고 `modelUsage` 키도 같았다. effort는 실행 기록에 나오지 않아 관측하지 못했다(unknown). lead는 첫 실행 한 번만 `claude-opus-5-5`(사용자 기본 모델)로 잡혔고 이후 세 번은 프로젝트 설정대로 `claude-fable-5-1`이었다. 원인은 확인하지 못했으므로 lead 모델을 바꾼 뒤에는 두 번 이상 실행해 본다. 같은 날 lead를 `claude-opus-5-5`로 바꿨다. 사용자 기본 모델도 Opus 5.5라서, lead 실행 확인만으로는 프로젝트 설정이 적용됐는지까지 구분되지 않는다. Codex 쪽은 같은 날 사용자가 §8 절차로 확인했다.

## 3. 스킬

| 스킬 | 언제 | 출처 |
|---|---|---|
| verification-before-completion | 완료·통과를 말하기 전 | obra/superpowers (MIT) |
| systematic-debugging | 버그·테스트 실패·예상 밖 동작, 수정 제안 전 | obra/superpowers (MIT) |
| surgical-patch | 원인을 안 뒤 가장 좁은 계층만 고칠 때 | 자체 |
| safe-refactor | 동작을 보존하는 구조 변경 | 자체 |
| verify-and-stop | 검증 전용 요청, 마지막 증명 | 자체 |
| gitnexus-exploring · impact-analysis · debugging · refactoring · guide · cli | 코드 그래프로 구조·영향·버그·리팩터링 분석 | GitNexus 1.6.12 (PolyForm Noncommercial) |

작업에 해당하는 스킬만 읽는다. 스킬은 권한을 넓히지 않는다.

**역할이 스킬을 실제로 쓰게 하는 장치.** 2026-09-25 하네스 이식 세션에서 스킬 호출은 lead·qa·reviewer 모두 0건이었다. 원인은 셋이었다. 역할 파일에 `tools:`를 적으면 그 밖의 도구는 주어지지 않는데 목록에 Skill이 없어 역할이 스킬을 부를 수 없었다(`claude -p --agent qa` 실측). 역할 본문에 스킬 지시가 없었다. lead도 내용을 안다고 스킬을 불러오지 않았다. 그래서 세 가지를 바꿨다. `scripts/harness.py`가 모든 역할에 Skill과 읽기 전용 GitNexus MCP 도구를 준다(목록은 `.claude/settings.json` allow와 같다). 역할 본문마다 기본 스킬을 지정하고 결과에 사용한 스킬을 적게 한다. `AGENTS.md` §8이 위임 지시문에 스킬 이름을 적도록 요구한다. 역할 파일의 `skills:` 항목으로 스킬 본문을 미리 넣는 방식은 `--agent` 실행에서 적재되지 않아 쓰지 않았다. `tests/test_harness_scripts.py`가 도구 목록과 역할 본문의 스킬 지시(존재하는 스킬만)를 검사한다. 실제 사용 여부는 세션 기록(`~/.claude/projects/<프로젝트>/<세션>.jsonl`)에서 `"type":"tool_use"` 중 `"name":"Skill"` 수로 확인한다. 스킬 원본은 `.claude/skills/`이고, `.agents/skills/`는 render가 만드는 사본이다. Windows에서 `core.symlinks=false`면 심볼릭 링크가 링크 텍스트 파일로 체크아웃되어 Codex가 스킬을 읽지 못하므로 링크 대신 사본을 쓴다.

## 4. 검증

```sh
python scripts/verify.py                 # render 검사 → 하네스 테스트 → ruff → 기동 → alembic heads → pytest (+ frontend/ 변경 시 flutter)
python scripts/verify.py --fast          # render 검사·ruff·기동·alembic heads만
python scripts/verify.py --frontend      # flutter analyze/test 강제
python scripts/verify.py --frontend-only # Docker 없이 render 검사와 flutter만
```

단계와 원 명령:

| 단계 | 명령 | 실행 위치 |
|---|---|---|
| render_check | `python scripts/harness.py render --check` | 로컬 python |
| harness_tests | `python -m pytest tests -q` | 로컬 python(pytest 필요) |
| docker_ready | `docker compose ps --status running -q backend` | 호스트 |
| backend_ruff | `docker compose exec -T backend python -m ruff check .` | backend 컨테이너 |
| backend_import | `docker compose exec -T backend python -c "import app.main"` | backend 컨테이너 |
| alembic_heads | `docker compose exec -T backend alembic heads` → `(head)` 한 줄 | backend 컨테이너 |
| backend_pytest | `docker compose exec -T -e TEST_DATABASE_URL=… -e TEST_DATABASE_ADMIN_URL=… backend pytest tests/ -q --junitxml=/tmp/harness-junit.xml` 뒤 `docker compose cp`로 회수 | backend 컨테이너 |
| flutter_analyze | `flutter analyze` | `frontend/` |
| flutter_test | `flutter test --file-reporter json:…` | `frontend/` |

- 백엔드 단계는 `docker compose up -d`로 띄운 backend 컨테이너 안에서 돈다. `backend/`가 `/app`에 바인드 마운트되므로 워킹트리의 코드가 그대로 검사된다. 컨테이너가 없으면 `docker_ready`에서 `backend_container_not_running`으로 멈춘다. ruff는 `backend/requirements.txt`에 있으므로 requirements를 바꿨으면 `docker compose build backend && docker compose up -d backend`로 이미지를 갱신한다.
- 기동 검사는 `import app.main`이다. pytest를 전부 통과하고도 앱이 못 뜨는 커밋(진입점 import 오류, 라우터 등록 오류)을 걸러낸다. `alembic heads`는 마이그레이션 head가 갈라졌는지 본다.
- flutter는 PATH에서 찾고, 없으면 `FLUTTER_ROOT`(또는 `FLUTTER_HOME`)`/bin/flutter`를 쓴다. Claude Code 세션에서는 `.claude/settings.local.json`의 `env.FLUTTER_ROOT`로 준다.
- 결과는 `.harness/runs/<YYYYmmdd-HHMMSS>-<8hex>/`의 `result.json`, `harness-junit.xml`, `junit.xml`(backend pytest), `flutter-tests.json`에 남는다. `result.json`은 `status`, `reason`, `failed_step`, `base_commit`, 실행 전후 `workspace_sha256`(추적+미추적 파일 내용 해시), `evidence_sha256`, `steps[]`의 명령·exit code·출력 꼬리·결과 합계·`evidence_error`·`check_error`, pytest `summary`를 담는다. 보고와 커밋 메시지의 수치는 이 파일의 값을 쓴다.
- 테스트 명령이 exit 0이어도 결과 파일이 없으면 `junit_missing`, 0건이면 `zero_tests`, 실패·오류가 기록돼 있으면 `junit_unsuccessful`로 실패 처리한다. flutter JSON 리포터는 `done` 이벤트가 없으면 증거로 보지 않는다.
- 실행 중 워킹트리가 바뀌면 `reason: workspace_mutated`로 실패 처리한다. 증거가 어느 트리를 말하는지 알 수 없기 때문이다.
- 하네스 스크립트 자체는 `tests/test_harness_scripts.py`가 검증한다. render drift 감지, 생성물 형식, 스킬 사본 동기화, 역할 파일이 규칙 전문을 복사하지 않는지, 역할 표 세 곳과 `agents.toml`의 일치, `.claude/settings.json`의 lead 모델·`.env` 차단·git 확인 항목, verify의 요약 파싱과 증거 판정을 본다.
- 테스트 통과와 스크린샷은 화면 품질의 증거가 아니다. 프론트 변경은 사람이 앱을 열어 확인할 화면과 상태를 보고에 적는다.
- 실제 Gemini를 호출하는 통합 검증(`python -m app.cli.ai validate-integration`)은 게이트에 넣지 않는다. 사용자가 명시적으로 요청할 때만 돌린다.
- **테스트 격리.** compose는 `backend/.env` 전체를 backend 컨테이너의 환경변수로 넣고, 설정 객체도 `/app/.env` 파일을 읽는다. 그래서 `backend/tests/conftest.py`가 app import 전에 세 가지를 한다. 설정 필드와 같은 이름의 환경변수를 지우고(DB·Redis·OpenSearch 주소 4개만 유지) `.env` 파일을 읽지 않는 설정 함수로 바꿔 로컬과 CI가 같은 코드 기본값으로 테스트하게 한다. `GEMINI_API_KEY`는 가짜 값으로 덮어쓴다. 루프백과 테스트 DB·Redis 외의 이름 해석·소켓 연결을 차단한다. OpenSearch 주소는 루프백이어도 차단한다. CI에서는 `localhost:9200`이라 루프백 허용에 걸려 연결 거부만 조용히 삼켜지기 때문이다. 서비스 코드가 `except Exception`으로 차단 예외를 삼키면 테스트가 저하 경로로 통과할 수 있으므로, 차단 시도를 기록해 두고 테스트 종료 시 기록이 있으면 그 테스트를 오류로 처리한다. 차단을 일부러 확인하는 테스트는 `expect_network_block` 픽스처를 쓴다. 기본값과 다른 설정이 남아 있으면 `pytest_configure`가 이름만 적어 멈춘다. `verify.py`의 backend_pytest 단계도 CI와 같은 가짜 키(`dummy-key-for-test`)를 넘긴다. `docker compose exec backend pytest`로 직접 돌려도 격리된다. 대역을 빠뜨린 테스트는 `외부 네트워크 접속을 차단했습니다`로 실패한다. 키를 빈 값으로 두면 `genai.Client` 생성에서 60건이 실패하므로 가짜 값을 쓴다. `backend/tests/test_network_isolation.py`가 이 격리를 검사한다. 2026-09-25 도입 시 로컬 `.env` 값에 기대던 테스트는 없었다. 종료 시 검사를 넣자 `test_catalog_apply_requires_confirmation_for_full_reindex`가 OpenSearch 삭제 호출을 대역 없이 하고 있던 것이 드러나 대역을 추가했다(reviewer 지적).
- **마이그레이션 검증.** 테스트 스키마는 `create_all`로 만들어지므로 일반 테스트는 마이그레이션을 실행하지 않는다. `backend/tests/test_migrations.py`(`migration` 마커)가 전용 임시 DB(`*_migration_test`)를 만들어 upgrade head → `alembic check` → downgrade base(테이블·enum 잔여 없음) → 재upgrade → `alembic check`를 돌리고 DB를 지운다. alembic은 별도 프로세스로 실행한다. `alembic/env.py`가 앱 설정의 DB 주소를 쓰므로 테스트 프로세스 안에서 돌리면 캐시된 설정의 DB를 건드릴 수 있기 때문이다. 이 테스트는 일반 pytest에 포함돼 `verify.py`와 CI backend-test 잡에서 그대로 돈다. 2026-09-25 도입 시 qa가 계약 기준으로 먼저 작성해 두 결함을 드러냈다. 모델의 `ai_generation_traces.started_at` 기본값이 마이그레이션에 없었고(`4d4ea61f1957`로 추가), 초기 마이그레이션의 downgrade가 enum 타입 6개를 남겨 재upgrade가 실패했다(downgrade에 타입 삭제 추가). 실행 시간은 약 10~16초다.

## 5. 변경 묶음 나눠 올리기

여러 주제가 섞인 변경을 의미 단위로 나눠 커밋하는 절차다. 각 커밋 시점에도 저장소가 검증을 통과해야 한다.

백엔드 검증은 메인 트리의 `backend/`를 마운트한 컨테이너에서 돌기 때문에, 격리 worktree를 만들어도 백엔드 단계는 worktree가 아니라 메인 트리를 검사한다. 그래서 이 프로젝트는 메인 트리에서 후보만 남기는 방식을 쓴다.

1. 이번 커밋에 넣지 않을 변경을 `git stash push -- <paths>`로 치운다(미추적 파일은 `-u`).
2. 남은 후보로 `python scripts/verify.py`를 돌린다. 프론트만이면 `--frontend-only`.
3. 단독으로 성립하지 않는 파일은 순서를 잡아 하나씩 얹으며 매 단계 검증한다. 예: 서비스를 먼저, 라우터를 뒤에. 스키마를 먼저, Flutter repository를 뒤에.
4. 통과한 파일만 `git commit -m "..." -- <paths>`로 커밋한다.
5. `git stash pop`으로 나머지를 되돌리고 반복한다.

## 6. Git 규칙

- 커밋 메시지 규칙은 `AGENTS.md` §7에 있다. 저장소 이력에서 뽑은 관례다: 한국어 제목 한 줄, 영역 scope, 파일 1~2개 단위, 본문과 트레일러 없음. `.githooks/commit-msg`가 형식을 검사한다(`core.hooksPath=.githooks`).
- 커밋은 사용자가 명령할 때만 만든다. 작업을 끝냈다고 스스로 커밋하지 않는다. push·`reset --hard`·강제 push는 사용자 확인이 필요하다.
- `.gitattributes`가 텍스트 파일을 LF로 고정한다. Windows `core.autocrlf=true` 체크아웃의 CRLF 경고를 없애고 `workspace_sha256`을 OS 간에 안정시킨다.

## 7. CI

`.github/workflows/ci.yml`이 main·develop의 push와 PR마다 세 잡을 돌린다.

| 잡 | 내용 |
|---|---|
| harness-check | `scripts/harness.py render --check`, 하네스 자체 테스트 |
| backend-test | ruff, `import app.main`, alembic head 단일 검사, PostgreSQL(pgvector)·Redis 서비스 컨테이너로 pytest |
| flutter-quality | `flutter pub get`, `flutter analyze`, `flutter test` |

CI는 설치 시점의 최신 라이브러리를 받는다. 로컬 이미지와 버전이 달라 생기는 실패는 CI가 먼저 알려 준다. lock 파일 도입은 별도 과제다.

## 8. Codex

Codex도 같은 `AGENTS.md`·역할 본문·스킬을 쓴다. 아래는 Claude Code와 다른 점만 적는다. ai-trade-manager에서 Codex 0.156으로 실측한 내용을 그대로 적용했다.

- **설정이 적용되는 조건.** Codex는 신뢰한 프로젝트에서만 `.codex/config.toml`과 `.codex/agents/`를 읽는다. 신뢰 목록은 사용자 Codex 설정(`$CODEX_HOME/config.toml`, 기본 `~/.codex`)의 `[projects.'<경로>'] trust_level = "trusted"`다. 예전 버전이 기록한 `\\?\C:\...` 형식 키는 인식되지 않아 프로젝트 설정 전체가 조용히 무시된다. `C:\...` 형식 키를 두거나 이 폴더에서 Codex를 열어 신뢰를 다시 승인한다.
- **lead 설정.** `.codex/config.toml`은 `[lead]` 모델·effort, `approval_policy = "on-request"`, `sandbox_mode = "workspace-write"`, 샌드박스 네트워크 차단(`git push`·패키지 설치는 승인 요청으로 올라온다), 동시 하위 에이전트 2개로 구성된다. `.mcp.json`의 GitNexus MCP 서버도 render가 옮긴다.
- **읽기 전용 역할.** 역할 파일에 `sandbox_mode = "read-only"`를 넣지만, 하위 에이전트는 lead의 샌드박스를 그대로 물려받는다. Codex에서 scout·reviewer의 읽기 전용은 역할 지시로 지킨다.
- **`.env` 차단.** Codex에는 파일 단위 읽기 차단을 두지 않았다. `AGENTS.md` §7 규칙으로 막는다.
- **스킬.** `.agents/skills/`는 `.claude/skills/`의 사본이다. 심볼릭 링크가 아니므로 `core.symlinks` 설정과 무관하게 동작한다.

모델 호출 없이 Codex가 무엇을 보는지 확인할 때는 `codex debug prompt-input "hi"`를 쓴다. `AGENTS.md` 적재, 스킬 목록과 경로, 적용된 샌드박스가 나온다. 실행 모델은 `$CODEX_HOME/state_5.sqlite`의 `threads` 표에서 `model`·`reasoning_effort`·`agent_role`을 읽어 확인한다.

## 9. 코드 그래프 (GitNexus)

```sh
SCARF_ANALYTICS=false DO_NOT_TRACK=1 npm i -g gitnexus@1.6.12   # 최초 1회. 설치 통계 전송을 끈다
gitnexus analyze                                  # 인덱싱. .gitnexusrc 기본값이 적용된다
gitnexus status                                   # 인덱싱 시점 커밋·파일과 비교 (커밋만 바뀌어도 stale)
gitnexus impact <심볼> --repo . --file <경로>      # 편집 전 호출자·위험도
gitnexus detect-changes --scope staged --repo .   # 커밋 전 영향받는 실행 흐름
```

- 인덱스는 워킹트리 파일 내용 기준이다. 2026-09-25 이 머신에서 첫 인덱싱은 약 2분(실제 분석 29초), 파싱 캐시가 있는 재인덱싱은 약 35초였다. 결과는 5,324 노드, 10,521 간선, 289 실행 흐름이었다.
- 다시 인덱싱할 때는 파일을 수정했을 때다. `gitnexus status`는 인덱싱 당시 커밋과 현재 커밋이 다르면 stale로 표시하므로, 기존 변경을 커밋만 한 경우에는 경고가 떠도 그래프는 정확하다.
- `.gitnexusrc`가 `skipAgentsMd`·`skipSkills`·`noStats`를 켜 둔다. 이게 없으면 analyze가 `AGENTS.md`와 `CLAUDE.md` 양쪽에 같은 안내 블록을 넣고(`CLAUDE.md`가 `AGENTS.md`를 import하므로 이중 적재), render가 관리하는 `.agents/skills/`에 스킬을 써서 `render --check`가 실패한다. `tests/test_harness_scripts.py`가 이 설정과 규칙 파일에 주입 블록이 없는지를 검사한다.
- `.mcp.json`이 `cmd /c gitnexus mcp`로 MCP 서버를 띄우고, `.claude/settings.json`의 `enabledMcpjsonServers`가 승인 없이 켠다. 새 세션부터 `impact`·`context`·`query`·`detect_changes`·`rename`·`trace`·`route_map` 등의 도구가 생긴다. 읽기 전용 도구만 allow에 넣었다. 2026-09-25 `claude -p`로 확인한 결과 서버가 `connected`로 떴고 도구 17개가 노출됐다.
- Dart 문법은 GitNexus 패키지에 들어 있는 네이티브 바이너리(win32-x64)로 읽는다. 설치 후 누락 경고가 없으면 정상이다.

**그래프 정확도 실측 (2026-09-25).** 텍스트 검색 결과를 기준값으로 대조했다.

| 대상 | 호출 방식 | 그래프 | 기준값 |
|---|---|---|---|
| `get_current_user` | FastAPI `Depends(...)` | 22 | 22 |
| `RAGService.search` | `self.rag_service.search(...)` | 4 | 4 |
| `AIService.recommend_diet` | `self.ai_service.recommend_diet(...)` | 1 | 1 |
| `NeoPrimaryButton` | Dart 위젯 생성자 | 13개 파일 + import만 한 파일 | 13개 파일 |
| `DietRepository.createDietLog` | `ref.read(dietRepositoryProvider).createDietLog(...)` | 0 (UNKNOWN) | 3 |
| `DietRepository.getDietLogs`, `getRecommendation` | 같은 provider 경유 | 0 (UNKNOWN) | 각 1 |
| `dietRepositoryProvider` | provider 변수 참조 | 0 | 8 |
| FastAPI 라우트의 Flutter 소비자 | Dio 경로 문자열 | 0 (`route_map` 라우트 26개는 모두 찾음) | 라우트별 1개 이상 |

- Python 백엔드는 이번 표본에서 정확했다. Dart는 Riverpod provider를 거치는 호출과 FastAPI↔Flutter 경계가 비어 있다. 이 두 경우는 반드시 텍스트 검색으로 교차 확인한다.
- `detect-changes`는 추적 중인 파일의 diff만 본다. 실측에서 `--scope all` 결과의 파일 수가 `git diff --name-only HEAD`와 같았고 미추적 새 파일은 빠졌다. 커밋 전에는 stage한 뒤 `--scope staged`로 본다.
- 첫 인덱싱에서 `frontend/lib/features/auth/data/`와 `chat/data/`의 repository 두 파일이 빠졌다. 원인은 Docker 볼륨용으로 둔 앵커 없는 `data/` 무시 규칙이었다. 파일은 이미 추적 중이라 git에는 보였지만 GitNexus는 무시 규칙을 따른다. 규칙을 `/data/`로 좁혀 해결했다. 인덱스에서 파일이 빠지면 `git check-ignore -v --no-index <경로>`로 먼저 확인한다.
- 라이선스는 PolyForm Noncommercial 1.0.0이다. 비상업적 개인 사용 범위에서만 쓴다.

## 10. 변경 이력

`harness/agents.toml`의 `harness_version`이 버전 원본이다.

| 버전 | 날짜 | 내용 |
|---|---|---|
| 1.0 | 2026-09-25 | ai-trade-manager 하네스 1.0 이식: `AGENTS.md` 규칙 재작성(권한·안전·검증·완료·위임 기준), `CLAUDE.md`, `.claude/settings.json`(lead 모델 고정, `.env` 차단, git 확인), 역할 5종(scout·backend·frontend·qa·reviewer)과 생성기, Codex용 스킬 사본 생성, 절차 스킬 5종, `verify.py`(Docker 컨테이너 기반 백엔드 게이트 + flutter JSON 증거), 하네스 자체 테스트, ruff 도입, `.gitattributes`, CI 세 잡(harness-check 추가, `flutter test` 추가) |
| 1.0 | 2026-09-25 | GitNexus 1.6.12 도입: `.gitnexusrc`로 규칙 파일 자동 주입과 스킬 설치 차단, `.mcp.json` MCP 서버(Codex 설정에도 반영), 스킬 6종과 라이선스 표기, `AGENTS.md` §10 사용 규칙, Python·Dart 호출자 정확도 실측, 앵커 없는 `data/` 무시 규칙을 `/data/`로 수정 |
| 1.0 | 2026-09-25 | lead 모델을 Opus 5.5로 변경(reviewer는 Fable 5.1 유지). Codex 역할 실행 확인 완료 |
| 1.0 | 2026-09-25 | 커밋 규칙을 저장소 이력(298개)에서 확인한 관례로 정리(트레일러 없음, 파일 1~2개 단위, 본문 생략). 백엔드 테스트 격리: 가짜 Gemini 키, 외부 네트워크 차단, 격리 회귀 테스트 4건 |
| 1.0 | 2026-09-25 | 테스트 설정을 로컬 `.env` 대신 코드 기본값으로 생성(인프라 주소만 유지), `backend/pytest.ini`(`--strict-markers`, `migration` 마커), 마이그레이션 왕복 테스트(qa 작성)와 결함 2건 수정(`started_at` 기본값 마이그레이션, 초기 downgrade의 enum 삭제) |
| 1.0 | 2026-09-25 | reviewer 지적 반영: 차단 예외가 서비스에서 삼켜져도 테스트 종료 시 실패, OpenSearch는 루프백이어도 차단(CI와 로컬 일치), 대역이 빠진 기존 테스트 1건 수정 |
| 1.0 | 2026-09-25 | 스킬 실사용 장치: 모든 역할에 Skill·GitNexus 읽기 MCP 도구, 역할 본문의 기본 스킬 지시와 보고, `AGENTS.md` §8 위임 지시문 스킬 명시·§9 불러서 따르기 규칙, 하네스 테스트 2건 |
