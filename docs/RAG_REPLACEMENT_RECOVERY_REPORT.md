# RAG Replacement Recovery Report

Last verified: 2026-06-20

## Summary

This report closes the v1 replacement recovery workflow as an operational portfolio artifact.

The recovery chain is:

```text
source failure lifecycle
-> replacement-preview
-> replacement-evaluate
-> catalog-replace-source --activate --evaluation-id
-> catalog-plan
-> catalog-review
-> catalog-apply
```

The key operating principle is that a failed source is not replaced by an arbitrary reachable URL. A candidate must first be previewed, evaluated for coverage/readiness, and passed through an activation gate before the catalog URL can change. Even after activation, RAG source rows, chunks, embeddings, and OpenSearch are updated only by the catalog plan/review/apply flow.

## Verified Recovery Boundaries

| Stage | Mutation boundary | Evidence |
|-------|-------------------|----------|
| Failure lifecycle | catalog state and plan items only | disabled/replacement-required policy records why a source is blocked |
| `replacement-preview` | audit row/report only | candidate fetch, parser, content hash, section/chunk count recorded in `rag_source_replacement_candidates` |
| `replacement-evaluate` | audit row/report only | coverage, parser, metadata, readiness, matched/missing terms recorded in `rag_source_replacement_evaluations` |
| activation gate | catalog JSON only | `catalog-replace-source --activate --evaluation-id` validates ready evaluation and previewed candidate |
| catalog apply | RAG corpus and OpenSearch | `catalog-plan -> catalog-review -> catalog-apply` remains the only corpus mutation path |

## Rejected Candidate Scenario

Representative live-style scenario:

```bash
docker compose exec backend python -m app.cli.rag replacement-preview \
  --file rag_sources/catalog.json \
  --key nih_ods_exercise_athletic_performance_fact_sheet \
  --candidate-url https://www.cdc.gov/nutrition/php/guidelines-recommendations/index.html \
  --report-path /tmp/RAG_REPLACEMENT_CANDIDATE_PREVIEW.md

docker compose exec backend python -m app.cli.rag replacement-evaluate \
  --candidate-id <candidate_id> \
  --report-path /tmp/RAG_REPLACEMENT_CANDIDATE_EVALUATION.md
```

Expected interpretation:

- The CDC nutrition URL can be fetched and parsed as an official source.
- It is not a suitable replacement for the NIH ODS exercise/athletic-performance supplement source.
- Evaluation should produce `rejected` or at least non-ready status because coverage terms for supplement, exercise, athletic performance, safety, and NIH ODS intent are missing.
- Activation must not proceed because only `ready_for_activation` evaluations are accepted by the gate.

This is the important safety signal: acquisition success is not treated as replacement suitability.

## Ready Candidate Scenario

Ready replacement is verified by deterministic test fixture rather than a live external source.

Test evidence:

- `tests/test_rag_replacement_evaluation_service.py`
  - verifies a semantically aligned candidate becomes `ready_for_activation`.
  - verifies mismatched or failed preview candidates are rejected.
- `tests/test_rag_replacement_activation_gate.py`
  - verifies only `ready_for_activation` plus `candidate_ready_for_activation` can activate.
  - verifies activation records `replacement_evaluation_id`, `replacement_candidate_id`, readiness score, and coverage score.
  - verifies the previous URL is preserved in `reference_urls`.

This keeps the portfolio evidence deterministic while live source availability remains outside local control.

## Activation Block Scenarios

The activation gate blocks catalog mutation before any file write when:

- `--activate` is used without `--evaluation-id`.
- evaluation id does not exist.
- evaluation status is `rejected` or `needs_manual_review`.
- evaluation recommendation is not `candidate_ready_for_activation`.
- evaluation catalog key does not match `--key`.
- evaluation candidate URL does not match `--replacement-url`.
- linked candidate is missing.
- linked candidate preview is not `preview_succeeded`.

These checks prove the operator cannot bypass preview/evaluation accidentally during catalog replacement.

## Verification Commands

```bash
python -m compileall backend\app backend\tests
docker compose exec backend alembic current
docker compose exec -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/health_trainer_test -e TEST_DATABASE_ADMIN_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres backend pytest tests/ -q
git diff --check
```

Expected result:

- Alembic current: `a2b3c4d5e6f7 (head)`
- Backend tests: `148 passed`
- No whitespace errors

Known non-blocking warnings:

- Windows LF/CRLF working tree warnings
- existing aiohttp deprecation warning in one catalog apply test

## Portfolio Signal

This workflow demonstrates operational RAG discipline:

- external source failures become explicit lifecycle state.
- candidate acquisition and semantic replacement suitability are separate decisions.
- activation requires audit evidence, not just operator intent.
- corpus mutation remains behind catalog plan/review/apply.
- every high-risk transition leaves reproducible DB and Markdown evidence.
