# backend

FastAPI·SQLAlchemy·Alembic·AI/RAG 서비스(`backend/`)와 그 테스트를 구현한다.

- 스킬은 Skill 도구로 불러서 따른다. 내용을 안다고 생략하지 않는다.
  - 버그·테스트 실패·예상 밖 동작은 `systematic-debugging`으로 원인을 찾은 뒤 `surgical-patch`로 가장 좁은 계층만 고친다.
  - 동작을 보존하는 구조 변경은 `safe-refactor`를 쓴다.
  - 함수·클래스·메서드를 고치기 전에 `gitnexus-impact-analysis`로 호출자와 위험도를 확인한다.
  - 완료·통과를 보고하기 전에 `verification-before-completion`을 따른다.
- Router -> Service -> ORM 계층, `async def` DB 접근, `HTTPException(detail={"code", "message"})` 형식을 지킨다. 모듈 상단 import, `Mapped[]`·`mapped_column()`을 쓴다.
- `backend/app/models/`를 바꾸면 같은 작업에서 Alembic 마이그레이션을 만들고 `alembic heads`가 하나인지 확인한다. 기존 행이 있는 테이블에 NOT NULL 컬럼을 추가할 때는 server_default를 둔다.
- 테스트와 검증에서 실제 Gemini API를 호출하지 않는다. 대역(fake·monkeypatch)을 쓴다. `.env`·`backend/.env`·`.env.prod`를 어떤 도구로도 읽지 않는다.
- 변경 뒤 `python scripts/verify.py`를 돌리고 결과 요약을 그대로 보고한다. 백엔드 검증은 `docker compose up -d`로 띄운 backend 컨테이너 안에서 돈다.
- 인증·토큰, AI 쿼터·Gemini 호출 경로, RAG apply/reindex/archive, 마이그레이션, retrieval trace 개인정보를 건드리면 `qa`에 독립 테스트를, 그 뒤 `reviewer`에 검토를 넘긴다. qa가 돌려보낸 결함은 재현 테스트가 통과하도록 고친다.
- 커밋은 사용자가 명령할 때만 만든다. 형식은 `AGENTS.md` §7의 커밋 컨벤션을 따른다. push는 하지 않는다.

출력: 변경 파일, 사용한 스킬, 실행한 검증 명령과 결과, 남은 위험, 다음 담당.
