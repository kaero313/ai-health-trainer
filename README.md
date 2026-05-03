# AI Health Trainer

AI 기반 개인 맞춤형 건강·피트니스 코칭 애플리케이션입니다.

문서는 역할 기준으로만 유지합니다.

| Document | Audience | Purpose |
|----------|----------|---------|
| `AGENTS.md` | AI 작업자 | Codex/AI가 작업할 때 지킬 실행 규칙 |
| `docs/OWNER_GUIDE.md` | 개발자/설계자/운영자인 사용자 | 제품 방향, 구현 현황, 개발/운영 기준 |
| `docs/*` 상세 설계 문서 | 개발자/설계자 | 기능별 상세 설계와 과거 구현 근거. 최신 상태 판단은 `OWNER_GUIDE.md` 우선 |

현재 상태:

- Phase 1~6 완료
- Backend tests: 74 PASS
- Flutter analyze: 0 issues

로컬 실행:

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
```

백엔드 API 문서:

- `http://localhost:8000/docs`

## Portfolio Focus

이 프로젝트의 핵심 포인트는 단순한 AI 채팅 앱이 아니라, 개인 건강 기록과 검증 가능한 지식 데이터를 결합하는 RAG 기반 AI 코칭 백엔드다.

- PostgreSQL: RAG source/chunk/version/status/trace의 source of truth
- OpenSearch: keyword + vector hybrid retrieval index
- pgvector: OpenSearch 장애 시 fallback과 재색인 원장
- CLI KnowledgeOps: URL fetch, catalog ingest, refresh, reindex, archive, evaluate, validate-v1
- Hybrid Chunking: official URL HTML을 Document -> Parent Section -> Child Evidence Chunk로 분해
- Traceability: retrieval trace와 generation trace를 저장해 AI 답변 근거를 추적

RAG 운영 명령:

```bash
docker compose exec backend python -m app.cli.rag ensure-index
docker compose exec backend python backend/scripts/ingest_rag_data.py --dir rag_data
docker compose exec backend python -m app.cli.rag fetch-preview --url https://www.cdc.gov/nutrition/php/guidelines-recommendations/index.html
docker compose exec backend python -m app.cli.rag ingest-catalog --file rag_sources/catalog.json
docker compose exec backend python -m app.cli.rag evaluate
docker compose exec backend python -m app.cli.rag validate-v1 --report-path /workspace/docs/RAG_EVALUATION_REPORT.md
docker compose exec backend python -m app.cli.rag parse-preview --file rag_data/nutrition_basics.md
docker compose exec backend python -m app.cli.rag refresh-source --source-id 1
docker compose exec backend python -m app.cli.rag decisions --job-id 1
```

상세 운영 기준은 `docs/RAG_OPERATIONS.md`를 기준으로 한다.

고급 RAG/AI 백엔드 포트폴리오 고도화 기준:

- `docs/RAG_ADVANCED_PORTFOLIO_ROADMAP.md`
- `docs/RAG_PIPELINE_ARCHITECTURE.md`
- `docs/RAG_DECISION_POLICY.md`
