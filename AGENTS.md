# AI Health Trainer - AI Worker Guide

> **Audience:** Claude Code·Codex 작업자
> **Purpose:** 새 세션의 AI가 프로젝트를 안전하게 이해하고 작업하기 위한 최소 계약서.
> **Human-facing source of truth:** `docs/OWNER_GUIDE.md`
> **Harness usage:** `docs/DEVELOPMENT_WORKFLOW.md`
> **Last updated:** 2026-10-03

응답과 코드 주석은 한국어로 짧고 직접적으로 쓴다. 요청 범위 안에서 구현하고 묻지 않은 리팩터링·추상화·의존성을 추가하지 않는다. 기존 사용자 변경은 보존한다.

---

## 1. Current State

AI Health Trainer는 개인 맞춤형 건강/피트니스 AI 코칭 앱이다.

| Area | Status |
|------|--------|
| Backend | FastAPI + PostgreSQL/pgvector + Redis + OpenSearch 완료 |
| Frontend | Flutter 모바일 우선 앱 완료, Web 개발 실행 지원 |
| AI/RAG | Gemini 3 Flash Preview + Gemini 2.5 Pro + `gemini-embedding-001` 완료 |
| Ops | Docker Compose, prod compose, Nginx, CI/CD, backup, health 완료 |
| Phase | Phase 1~6 완료 |
| Verification | `python scripts/verify.py` 게이트. 최신 수치는 마지막 `.harness/runs/<id>/result.json` |

새 작업은 **Phase 7 또는 릴리스 후보 작업**으로 정의한다.

---

## 2. Read First

AI 작업자는 작업 전 아래 순서로 읽는다.

1. `docs/OWNER_GUIDE.md` - 제품/개발/설계/운영 기준. 전체를 읽지 않고 §0 Document Map에서 작업과 관련된 절과 상세 문서를 찾아 읽는다
2. 관련 코드 - 실제 구현이 문서보다 우선한다
3. 현재 git 상태 - 사용자/다른 작업자의 변경을 되돌리지 않는다

`codex_prompts/`는 과거 프롬프트 아카이브이며 일반 작업 기준 문서가 아니다.

---

## 3. Local Run

Backend stack:

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
```

Flutter web:

```bash
cd frontend
flutter run -d web-server --web-hostname 127.0.0.1 --web-port 3000
```

Android:

- 에뮬레이터는 기본 주소(`10.0.2.2:8000`)로 붙는다. 실기기는 `adb reverse tcp:8000 tcp:8000` 뒤 `--dart-define=API_BASE_URL=http://127.0.0.1:8000/api/v1`로 실행한다.
- 개발용 compose는 호스트 포트를 `127.0.0.1`에만 연다. PC의 공유기 IP로는 접속되지 않는다.

Browser verification:

- UI 작업 시 브라우저 도구(Codex 앱 Browser Use 사이드 패널 또는 Claude Code 브라우저 도구)로 `http://127.0.0.1:3000`을 열어 확인한다.
- 외부 브라우저를 별도로 열지 않는다.

---

## 4. Verification

```bash
python scripts/verify.py                 # render 검사 → 하네스 테스트 → ruff → 기동 → alembic heads → pytest (+ frontend/ 변경 시 flutter analyze/test)
python scripts/verify.py --fast          # render 검사·ruff·기동·alembic heads만
python scripts/verify.py --frontend      # flutter analyze/test 강제
python scripts/verify.py --frontend-only # Docker 없이 render 검사와 flutter만
```

- 백엔드 단계는 `docker compose up -d`로 띄운 backend 컨테이너 안에서 돈다. 원 명령은 `docs/DEVELOPMENT_WORKFLOW.md` §4에 있다.
- 결과는 `.harness/runs/<id>/result.json`에 남는다. 보고와 커밋 메시지에 적는 수치는 이 파일의 값이어야 한다. README·OWNER_GUIDE의 테스트 수는 사람용 스냅숏이므로 기준값으로 인용하지 않는다.

---

## 5. Backend Rules

- Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2를 따른다.
- DB 접근 함수는 `async def`로 작성한다.
- Router -> Service -> ORM 패턴을 유지한다.
- FastAPI 인증 의존성은 `from app.core.deps import get_current_user`를 사용한다.
- SQLAlchemy 모델은 `Mapped[]`, `mapped_column()`을 사용한다.
- 모델 파일에는 `from __future__ import annotations`를 사용한다.
- import는 모듈 상단에 둔다. 함수/메서드 내부 import는 피한다.
- 에러 응답은 `HTTPException(detail={"code": "...", "message": "..."})` 형식을 따른다.
- pgvector 차원은 `gemini-embedding-001` 기준 `3072`다.
- `backend/app/models/`를 바꾸면 같은 작업에서 Alembic 마이그레이션을 만들고 `alembic heads`가 하나인지 확인한다. 기존 행이 있는 테이블에 NOT NULL 컬럼을 추가할 때는 server_default를 둔다.
- 모델의 `server_default`·`nullable`·타입은 마이그레이션에도 같게 반영한다. 모든 마이그레이션은 downgrade를 구현하고, upgrade에서 만든 enum 같은 타입도 downgrade에서 지운다. `backend/tests/test_migrations.py`가 전용 임시 DB에서 upgrade head → `alembic check` → downgrade base → 재upgrade를 검사한다. 테스트 스키마는 `create_all`로 만들어지므로 이 테스트가 마이그레이션을 실행하는 유일한 곳이다.
- 린트 규칙은 `backend/ruff.toml`(E4·E7·E9·F)이다.

Common error codes:

| HTTP | Code |
|------|------|
| 400 | `VALIDATION_ERROR`, `AI_BLOCKED` |
| 401 | `UNAUTHORIZED` |
| 404 | `NOT_FOUND` |
| 409 | `CONFLICT` |
| 429 | `DAILY_LIMIT_EXCEEDED` |
| 502 | `AI_PARSE_ERROR` |
| 503 | `AI_TIMEOUT`, `AI_RATE_LIMITED`, `AI_SERVICE_ERROR` |

---

## 6. Frontend Rules

- Flutter + Riverpod + GoRouter + Dio 구조를 유지한다.
- 사용자 대면 문구는 한국어로 작성한다.
- 디자인은 다크 모드 기반, Material 3 톤, `frontend/lib/core/theme/`의 색·간격과 `frontend/lib/shared/widgets/neo_widgets.dart` 공통 위젯을 따른다. 세부 기준은 `docs/FLUTTER_UI_DESIGN.md`다.
- shadcn_ui 기반 새 디자인 시스템은 `docs/DESIGN_SYSTEM.md`가 목표 문서이고 토큰은 `frontend/lib/core/design_system/`에 있다. 이 작업에는 `shadcn-ui-flutter` 스킬을 쓴다. 기존 화면을 새 체계로 옮기는 작업은 사용자가 지시할 때만 한다.
- UI 변경 후 `python scripts/verify.py --frontend`를 돌리고 브라우저에서 실제 화면을 확인한다. 테스트 통과와 스크린샷은 화면 품질의 증거가 아니므로, 사람이 확인할 화면·상태를 보고에 적는다.
- 로그인 화면에는 테스트 계정 기본값이 없다. 로컬 개발 계정은 `docker compose exec backend python scripts/create_admin.py`로 만들고, 비밀번호는 `ADMIN_PASSWORD` 환경변수로 주거나 스크립트가 무작위로 만들어 한 번 출력한다.

---

## 7. Git And Safety

- 사용자가 만든 변경을 되돌리지 않는다.
- `.env`, `backend/.env`, `.env.prod`, `.env.local`은 어떤 도구로도 읽지 않고 절대 stage하지 않는다. Claude Code의 Read 차단(`.claude/settings.json`)은 Bash `cat`까지 막지 못하고 Codex에는 파일 단위 읽기 차단이 없으므로 이 규칙으로 보완한다. 비밀값은 커밋하지 않는다.
- 테스트와 검증에서 실제 Gemini API를 호출하지 않는다. 대역(fake·monkeypatch)을 쓴다. `backend/tests/conftest.py`가 로컬 `.env` 대신 코드 기본값으로 설정을 만들고(인프라 주소만 유지), 실제 키를 가짜 키로 덮어쓰고, 루프백·테스트 DB·Redis 외의 네트워크 접속(OpenSearch는 루프백이어도)을 차단하므로, 대역을 빠뜨린 테스트는 실패한다. 서비스 코드가 차단 예외를 삼켜도 차단 기록이 남아 그 테스트는 종료 시점에 오류로 처리된다. 차단을 일부러 확인하는 테스트만 `expect_network_block` 픽스처를 쓴다. 이 격리를 끄거나 우회하지 않는다. 실제 Gemini를 호출하는 통합 검증(`python -m app.cli.ai validate-integration`)과 RAG ingest/reindex/apply는 사용자가 명시적으로 요청할 때만 실행한다.
- 커밋은 사용자가 명령할 때만 만든다. 작업을 끝냈다고 스스로 커밋하지 않고 변경은 워킹트리에 둔 채 보고한다. `git push`·`git reset --hard`는 사용자 확인이 필요하다. 강제 push와 이력 재작성은 하지 않는다.
- 브랜치를 만들지 않고 `main`에 바로 커밋한다(1인 개발, 2026-10-04 기준 커밋 312개 중 merge 0개). 기본 브랜치에서는 브랜치부터 만들라는 도구 기본 지시보다 이 규칙이 우선한다. 오래 걸리는 큰 작업에 브랜치를 쓸지는 사용자가 정한다.
- 테스트 수가 바뀐 변경을 커밋할 때는 README·OWNER_GUIDE의 현재 상태 수치를 그 커밋을 검증한 `result.json` 값으로 같은 묶음에서 갱신한다.
- 커밋 컨벤션은 이 저장소 이력(2026-09-25 기준 298개)에서 확인한 관례를 따른다. 형식 검사는 `.githooks/commit-msg`가 한다.
  - 제목: `<type>(<scope>): <한국어 설명>` 한 줄, 100자 이내. 설명은 `정리`·`추가`·`수정`처럼 명사형으로 짧게 끝낸다(예: `feat(ui): 운동 저장소 정리`).
  - type: `feat`, `fix`, `docs`, `test`, `chore`, `build`, `refactor`, `ci`, `style`, `perf`.
  - scope: 바뀐 영역을 쓴다. 자주 쓰는 값은 `ai`, `ui`, `db`, `api`, `dashboard`, `diet`, `exercise`, `auth`, `profile`, `rag`, `web`, `config`, `infra`, `test`이고, 하네스 변경은 `harness`를 쓴다. 영역이 없으면 생략한다(`chore: ...`).
  - 크기: 한 커밋에 파일 1~2개가 기본이다. 모델·마이그레이션·서비스·API·UI·테스트·문서 단위로 잘게 나눈다.
  - 본문은 쓰지 않는 것이 기본이다. 제목만으로 설명할 수 없는 결정이 있을 때만 쓴다.
  - 트레일러(Co-Authored-By 등)는 붙이지 않는다. 294개 커밋이 트레일러 없이 작성됐다.
- 섞인 변경을 나눠 커밋할 때는 각 중간 상태가 검증을 통과하도록 순서를 잡는다(`docs/DEVELOPMENT_WORKFLOW.md` §5).

---

## 8. Harness: Roles And Delegation

이 저장소의 멀티 에이전트는 앱 기능이 아니라 Claude Code·Codex 개발 워크플로우다. 역할·모델·effort·허용 경로의 원본은 `harness/agents.toml`과 `harness/roles/*.md`다. 생성물 `.claude/agents/*.md`, `.codex/agents/*.toml`, `.codex/config.toml`, `.agents/skills/**`는 직접 편집하지 않고 `python scripts/harness.py render`로 갱신한다.

- 대화를 시작한 세션이 lead다. 기본 모델은 Claude Code가 Opus 5.5, Codex가 GPT-6 Sol이고 effort는 xhigh다(`agents.toml`의 `[lead]`). 다른 에이전트를 부를 수 있는 것은 lead뿐이다.

| 역할 | 모델 (Claude / Codex) | effort | 쓰기 | 용도 |
|---|---|---|---|---|
| scout | Sonnet 5 / GPT-6 Luna | low | 없음 | 코드 경로·영향 범위·API 계약 양끝 조사 |
| backend | Opus 5.5 / GPT-5.6 Terra | high | `backend/` `docs/` | FastAPI·DB·AI/RAG 서비스·테스트 |
| frontend | Opus 5.5 / GPT-5.6 Terra | high | `frontend/` `docs/` | Flutter 화면·상태·위젯 테스트 |
| qa | Opus 5.5 / GPT-6 Sol | high | `backend/tests/` `frontend/test/` | 위험 경로 변경의 계약 기준 독립 테스트 |
| reviewer | Fable 5.1 / GPT-6 Sol | xhigh | 없음 | 독립 검토, 소스 수정 금지 |

- **위임 기준.** 몇 개 파일의 수정과 대화하며 방향을 잡는 작업은 lead가 직접 한다. 서브에이전트는 빈 맥락에서 시작해 파일을 다시 읽고 결과를 요약으로만 돌려주므로, 작은 작업은 맡기는 비용이 더 크다. 여러 파일에 걸쳐 lead의 맥락을 크게 차지할 구현은 backend·frontend에 맡기고, 서로 독립인 서버·화면 작업은 둘에 나눠 병렬로 맡긴다. 같은 파일이나 같은 모듈 ownership을 두 역할에 동시에 주지 않는다. 영향 범위가 넓은 조사는 scout에 맡긴다.
- **위험 경로 게이트.** 인증·토큰(JWT, refresh), AI 쿼터·Gemini 호출 경로(일일 한도·비용), AI 프롬프트·안전 설정(`backend/app/services/ai_service.py`의 프롬프트 상수·`SAFETY_SETTINGS`), RAG 운영 명령(ingest·register·refresh·apply·reindex·archive), Alembic 마이그레이션, retrieval trace 개인정보, 배포 설정을 건드리는 변경은 누가 구현했든 qa의 독립 테스트와 reviewer 검토를 거친다. qa는 구현이 아니라 계약을 기준으로 실패 경로 테스트를 쓰고, reviewer는 그 테스트와 diff를 함께 본다. 작성자의 자체 점검을 독립 검토로 표시하지 않는다.
- **위임할 때 스킬 명시.** 서브에이전트는 빈 맥락에서 시작하고, 세션 시작 시점의 `AGENTS.md` 사본을 받는다. 그래서 lead는 위임 지시문에 그 작업에 적용할 스킬 이름을 직접 적는다(예: 버그 수정은 `systematic-debugging`·`surgical-patch`, 영향 조사는 `gitnexus-impact-analysis`, 검토는 `verification-before-completion`). 역할 본문(`harness/roles/*.md`)에 기본 스킬이 있지만, 작업별로 무엇을 쓸지는 lead가 정한다. 모든 역할은 Skill 도구와 읽기 전용 GitNexus MCP 도구를 받는다. 결과 보고에는 실제로 사용한 스킬을 적게 하고, 적지 않았으면 쓰지 않은 것으로 본다.
- 지정 모델을 쓸 수 없거나 대체됐으면 중단하고 보고한다. 자동으로 낮추지 않는다. 요청한 모델과 실제 관측된 모델을 구분해 적고, 확인할 수 없으면 unknown이라고 쓴다.
- Codex의 하위 에이전트는 역할 파일의 `sandbox_mode`와 관계없이 lead의 샌드박스를 물려받는다(ai-trade-manager에서 Codex 0.156 실측). Codex에서 scout·reviewer의 읽기 전용은 역할 지시로 지킨다.

---

## 9. Verification And Completion

- 완료·통과를 말하기 전에 같은 메시지 안에서 검증을 실제로 돌리고 출력을 읽는다(`verification-before-completion`). skip·not_run·모델 대체를 통과로 표현하지 않는다. pytest 통과만으로 앱이 뜬다고 말하지 않는다(기동 검사가 따로 있는 이유).
- 도달할 수 없는 검증을 완료 조건으로 두지 않는다. 이 환경에서 실행할 수 없는 검증(예: Docker가 꺼져 있을 때의 백엔드 테스트)은 미실행으로 적고 남은 확인 항목으로 따로 넘긴다. 반대로 실행할 수 있는 검증을 미실행으로 남겨 두지 않는다.
- 테스트 통과와 스크린샷은 화면 품질의 증거가 아니다. 프론트 변경은 사람이 앱을 열어 확인할 화면과 상태를 보고에 적는다.
- 버그는 `systematic-debugging` → `surgical-patch`, 구조 변경은 `safe-refactor`, 검증 전용 요청은 `verify-and-stop`을 적용한다. 작업에 맞는 스킬만 읽는다. 스킬은 Skill 도구로 불러서 따르고, 내용을 이미 안다고 생략하지 않는다. 기억에 의존해 절차를 흉내 내면 빠지는 단계가 생긴다(2026-09-25 하네스 이식 세션에서 스킬 호출이 0건이었다). 스킬 원본은 `.claude/skills/`이고 Codex는 사본 `.agents/skills/`를 읽는다.

---

## 10. Code Graph (GitNexus)

GitNexus 1.6.12(전역 설치)로 Python과 Dart를 인덱싱한다. 인덱스 `.gitnexus/`는 커밋하지 않는다. `.gitnexusrc`가 규칙 파일 주입과 스킬 설치를 꺼 두었으므로 `gitnexus analyze`를 그대로 쓴다. 설정 이유, 소요 시간, 정확도 실측은 `docs/DEVELOPMENT_WORKFLOW.md` §9에 있다.

- 인덱스는 HEAD가 아니라 **워킹트리** 기준이다. **파일을 수정했으면** 그래프를 쓰기 전에 다시 인덱싱한다. scout·reviewer는 Bash가 없으므로, 그래프를 쓰는 작업을 맡기기 전에 lead가 `.gitnexus/meta.json`의 `indexedAt` 이후 바뀐 파일이 있는지 보고 필요하면 먼저 인덱싱한다. 커밋만 한 경우의 `stale` 표시는 무시한다.
- **함수·클래스·메서드를 고치기 전에** `gitnexus impact <이름> --repo . --file <경로>`(MCP `impact`)로 호출자와 위험도를 확인해 보고한다. HIGH·CRITICAL이면 편집 전에 사용자에게 알린다.
- **그래프만 믿지 않는다.** 호출자 0건이나 `risk: UNKNOWN`은 "쓰이지 않는다"는 뜻이 아니다. Riverpod provider를 거치는 Dart 호출(`ref.read(xxxProvider).method()`)과 FastAPI 라우트↔Flutter repository 호출은 그래프에 없으므로 텍스트 검색으로 확인한다. API 계약을 바꾸면 `frontend/lib/features/*/data/*_repository.dart`에서 경로 문자열을 검색한다.
- **커밋을 만들기 전에** `gitnexus detect-changes --scope staged --repo .`(MCP `detect_changes`)로 바뀐 심볼과 영향받는 실행 흐름을 확인해 보고한다. 미추적 새 파일은 stage한 뒤 본다. push 전 누적 변경은 `--scope compare --base-ref origin/main`으로 본다.
- 섞인 변경을 나눠 커밋할 때 후보가 HEAD에서 단독으로 성립하는지는 `git grep <심볼> HEAD`로 lead가 확인한다. 그래프는 후보와 영향 범위를 좁히는 데만 쓴다.
- 이름 변경은 MCP `rename`을 dry run으로 먼저 돌리고, 적용 뒤 텍스트 검색으로 남은 호출을 확인한다(provider 경유 호출은 `rename`도 놓친다).
- 스킬: 구조 파악 `gitnexus-exploring`, 영향 분석 `gitnexus-impact-analysis`, 버그 추적 `gitnexus-debugging`, 리팩터링 `gitnexus-refactoring`, 도구 안내 `gitnexus-guide`, CLI `gitnexus-cli`.
- PolyForm Noncommercial 1.0.0 라이선스다. 비상업적 개인 사용 범위에서만 쓴다.
