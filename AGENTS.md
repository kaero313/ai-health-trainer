# AI Health Trainer - AI Worker Guide

> **Audience:** Codex/AI 작업자
> **Purpose:** 새 세션의 AI가 프로젝트를 안전하게 이해하고 작업하기 위한 최소 계약서.
> **Human-facing source of truth:** `docs/OWNER_GUIDE.md`
> **Last updated:** 2026-04-25

---

## 1. Current State

AI Health Trainer는 개인 맞춤형 건강/피트니스 AI 코칭 앱이다.

| Area | Status |
|------|--------|
| Backend | FastAPI + PostgreSQL/pgvector + Redis 완료 |
| Frontend | Flutter 모바일 우선 앱 완료, Web 개발 실행 지원 |
| AI/RAG | Gemini 3 Flash Preview + Gemini 2.5 Pro + `gemini-embedding-001` 완료 |
| Ops | Docker Compose, prod compose, Nginx, CI/CD, backup, health 완료 |
| Phase | Phase 1~6 완료 |
| Verification | Backend tests 56 PASS, `flutter analyze` 0 issues |

새 작업은 **Phase 7 또는 릴리스 후보 작업**으로 정의한다.

---

## 2. Read First

AI 작업자는 작업 전 아래 순서로 읽는다.

1. `docs/OWNER_GUIDE.md` - 제품/개발/설계/운영 기준
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

Browser verification:

- UI 작업 시 Codex 앱 내 Browser Use 사이드 패널로 `http://127.0.0.1:3000`을 열어 확인한다.
- 외부 브라우저를 별도로 열지 않는다.

---

## 4. Verification

Backend tests:

```bash
docker compose exec \
  -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/health_trainer_test \
  -e TEST_DATABASE_ADMIN_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres \
  backend pytest tests/ -v --tb=short
```

Flutter analyze:

```bash
cd frontend
flutter analyze
```

현재 기준 검증값:

- `56 passed`
- `No issues found`

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
- 디자인은 다크 모드 기반, 그린/블루 액센트, Material 3 톤을 유지한다.
- UI 변경 후 Browser Use 사이드 패널에서 실제 화면을 확인한다.
- 로컬 테스트용 로그인 기본값은 릴리스 전 제거 대상이다.

---

## 7. Git And Safety

- 사용자가 만든 변경을 되돌리지 않는다.
- `.env`, `backend/.env`, `.env.prod`는 절대 stage하지 않는다.
- 커밋 컨벤션: `<type>(<scope>): <description>`
- 주요 type: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`
- 주요 scope: `auth`, `profile`, `diet`, `exercise`, `dashboard`, `ai`, `db`, `ui`, `infra`, `docs`

---

## 8. Multi-Agent Workflow

이 저장소에서 멀티 에이전트는 앱 기능이 아니라 Codex 개발 워크플로우다.

- 메인 Codex가 요청 해석, critical path 처리, 결과 통합을 맡는다.
- `explorer`: 코드베이스 탐색 전용
- `worker`: 명시된 write scope 안의 구현 전용
- `reviewer`: findings-first 리뷰 전용

Rules:

- 작은 문서/단일 파일 수정은 메인 Codex 단독으로 처리해도 된다.
- backend/frontend 동시 작업처럼 병렬 가치가 있으면 subagent를 사용한다.
- 같은 파일이나 같은 모듈 ownership을 두 `worker`에 동시에 주지 않는다.
- `agents.max_threads = 4`, `agents.max_depth = 1` 기준을 유지한다.
- worker에게는 “다른 사람 변경 revert 금지”와 write scope를 명시한다.
