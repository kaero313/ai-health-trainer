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
- CLI KnowledgeOps: URL fetch, catalog plan/apply, catalog ingest, refresh, reindex, archive, evaluate, validate-v1
- Hybrid Chunking: official URL HTML을 Document -> Parent Section -> Child Evidence Chunk로 분해
- Catalog Control Plane: official source 변경을 plan DB에 저장하고 run id 기준으로 review/apply
- Traceability: retrieval trace와 generation trace를 저장해 AI 답변 근거를 추적

RAG 운영 명령:

```bash
docker compose exec backend python -m app.cli.rag ensure-index
docker compose exec backend python backend/scripts/ingest_rag_data.py --dir rag_data
docker compose exec backend python -m app.cli.rag fetch-preview --url https://www.cdc.gov/nutrition/php/guidelines-recommendations/index.html
docker compose exec backend python -m app.cli.rag catalog-plan --file rag_sources/catalog.json --report-path /workspace/docs/RAG_CATALOG_PLAN_REPORT.md
docker compose exec backend python -m app.cli.rag catalog-plan --file rag_sources/document_catalog.json --report-path /workspace/docs/RAG_DOCUMENT_CATALOG_PLAN_REPORT.md
docker compose exec backend python -m app.cli.rag catalog-runs --limit 20
docker compose exec backend python -m app.cli.rag catalog-run --run-id <run_id>
docker compose exec backend python -m app.cli.rag catalog-review --run-id <run_id> --report-path /workspace/docs/RAG_CATALOG_REVIEW_REPORT.md
docker compose exec backend python -m app.cli.rag catalog-apply --run-id <run_id> --review-run-id <review_run_id>
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
- `docs/RAG_CATALOG_CONTROL_PLANE.md`

## RAG v1.5 Local Document Catalog

The catalog control plane also supports local MD/TXT/PDF sources through source adapters. Use `rag_sources/document_catalog.json` for reproducible internal summaries and parser fixtures while official source URLs remain metadata references.

```bash
docker compose exec backend python -m app.cli.rag catalog-plan --file rag_sources/document_catalog.json --report-path /workspace/docs/RAG_DOCUMENT_CATALOG_PLAN_REPORT.md
```

## RAG Official PDF URL Acquisition

The official source catalog now supports `acquisition_type=pdf_url` for small text-extractable PDF sources. v1 uses the ODPHP Physical Activity Guidelines Executive Summary PDF as an official grade A source. PDF URL items store binary fetch metadata, `etag`/`last_modified`, raw content hash, parser confidence, and page/paragraph chunk lineage; oversized or scanned PDFs stay blocked for manual review/OCR backlog.

```bash
docker compose exec backend python -m app.cli.rag catalog-plan --file rag_sources/catalog.json --report-path /workspace/docs/RAG_CATALOG_PLAN_REPORT.md
```

## RAG Scheduler / Plan Automation

Local-only operations now use a plan-only scheduler path. The scheduler checks official URL and local document catalogs, creates catalog plan runs, and writes an operations report. It does not change RAG data or OpenSearch; an operator still approves changes with `catalog-apply`.

```bash
docker compose exec backend python -m app.cli.rag scheduler-run --force-plan --report-path /workspace/docs/RAG_SCHEDULER_REPORT.md
docker compose exec backend python -m app.cli.rag scheduler-runs --limit 20
docker compose exec backend python -m app.cli.rag scheduler-run-detail --run-id <scheduler_run_id>
docker compose exec backend python -m app.cli.rag scheduler-review --run-id <scheduler_run_id> --report-path /workspace/docs/RAG_SCHEDULER_REVIEW_REPORT.md
docker compose exec backend python -m app.cli.rag catalog-review --run-id <catalog_plan_run_id> --report-path /workspace/docs/RAG_CATALOG_REVIEW_REPORT.md
docker compose exec backend python -m app.cli.rag review-runs --limit 20
docker compose exec backend python -m app.cli.rag review-run --run-id <review_run_id>
docker compose exec backend python -m app.cli.rag catalog-run --run-id <catalog_plan_run_id>
docker compose exec backend python -m app.cli.rag catalog-apply --run-id <catalog_plan_run_id> --review-run-id <catalog_review_run_id>
docker compose exec backend python -m app.cli.rag catalog-apply --run-id <catalog_plan_run_id> --review-run-id <catalog_review_run_id> --apply-approved-only
docker compose exec backend python -m app.cli.rag validate-v1 --report-path /workspace/docs/RAG_EVALUATION_REPORT.md
```

## RAG Source Failure Lifecycle

Official sources that repeatedly fail acquisition are managed as catalog state instead of blind retries. A failed source can be disabled, marked as requiring replacement, or linked to a manually curated fallback while the existing indexed source remains protected by review and apply gates.

```bash
docker compose exec backend python -m app.cli.rag catalog-disable-source --file rag_sources/catalog.json --key <catalog_key> --reason "HTTP 403"
docker compose exec backend python -m app.cli.rag replacement-preview --file rag_sources/catalog.json --key <catalog_key> --candidate-url <url> --report-path /tmp/RAG_REPLACEMENT_CANDIDATE_PREVIEW.md
docker compose exec backend python -m app.cli.rag catalog-replace-source --file rag_sources/catalog.json --key <catalog_key> --replacement-url <url>
docker compose exec backend python -m app.cli.rag catalog-enable-source --file rag_sources/catalog.json --key <catalog_key>
```

`replacement-preview` records a candidate audit row and Markdown report only. It does not update the catalog, RAG source/chunk rows, embeddings, or OpenSearch.

## RAG Review / Approval Layer

Catalog and scheduler plans are reviewed before apply. The review layer stores an audit record in `rag_review_runs` and `rag_review_items`, writes Markdown approval reports, and maps plan actions into operator-facing decisions such as `approve_partial_refresh`, `manual_confirm_full_reindex`, `blocked_manual_review`, and `fix_source_acquisition`.

Default operation order:

```text
scheduler-run -> scheduler-review -> catalog-review -> catalog-apply --review-run-id -> validate-v1
```

`catalog-apply` requires a completed `catalog-review` run. Scheduler reviews are aggregate evidence and cannot approve apply. Blocked review items stop the default apply path; `--apply-approved-only` explicitly applies only approved items and records blocked items as skipped. Full reindex items also require `--confirm-full-reindex`.

Review reports:

- `docs/RAG_SCHEDULER_REVIEW_REPORT.md`
- `docs/RAG_CATALOG_REVIEW_REPORT.md`
