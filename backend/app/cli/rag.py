from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.services.rag_catalog_control_service import RAGCatalogControlService
from app.services.rag_evaluation import evaluate_retrieval, load_retrieval_cases
from app.services.rag_service import RAGService


DEFAULT_EVAL_CASES_PATH = Path(__file__).resolve().parents[2] / "rag_eval" / "retrieval_cases.json"


def _split_tags(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


async def _ensure_index() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        await RAGService(db, settings).ensure_index()
    print(f"OpenSearch RAG index is ready: {settings.RAG_OPENSEARCH_ALIAS}")


async def _delete_index() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        await RAGService(db, settings).delete_index()
    print(f"OpenSearch RAG index deleted: {settings.RAG_OPENSEARCH_INDEX}")


async def _ingest(args: argparse.Namespace) -> None:
    settings = get_settings()
    content = Path(args.file).read_text(encoding="utf-8")
    async with AsyncSessionLocal() as db:
        chunk_count = await RAGService(db, settings).ingest_document(
            title=args.title,
            content=content,
            category=args.category,
            source=args.source_url or "",
            tags=_split_tags(args.tags),
            source_type=args.source_type,
            source_grade=args.source_grade,
            license_value=args.license,
            language=args.language,
            author_or_org=args.author_or_org,
        )
    print(f"Ingested {chunk_count} RAG chunks from {args.file}")


async def _parse_preview(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGService(db, settings).parse_preview(
            args.file,
            parser_type=args.parser,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _fetch_preview(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGService(db, settings).fetch_preview_url(
            args.url,
            title=args.title,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _register_source(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGService(db, settings).register_source(
            file_path=args.file,
            title=args.title,
            category=args.category,
            tags=_split_tags(args.tags),
            parser_type=args.parser,
            source_url=args.source_url or None,
            source_type=args.source_type,
            source_grade=args.source_grade,
            license_value=args.license,
            language=args.language,
            author_or_org=args.author_or_org,
            refresh_policy=args.refresh_policy,
            refresh_interval_hours=args.refresh_interval_hours,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _register_url(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGService(db, settings).register_url(
            url=args.url,
            title=args.title,
            category=args.category,
            tags=_split_tags(args.tags),
            source_type=args.source_type,
            source_grade=args.source_grade,
            license_value=args.license,
            language=args.language,
            author_or_org=args.author_or_org,
            refresh_policy=args.refresh_policy,
            refresh_interval_hours=args.refresh_interval_hours,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _ingest_catalog(args: argparse.Namespace) -> None:
    settings = get_settings()
    catalog_path = Path(args.file)
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    sources = payload.get("sources", []) if isinstance(payload, dict) else payload
    if not isinstance(sources, list):
        raise SystemExit("Catalog file must contain a sources list")

    results: list[dict[str, Any]] = []
    async with AsyncSessionLocal() as db:
        service = RAGService(db, settings)
        for source in sources:
            result = await service.register_url(
                url=source["url"],
                title=source.get("title"),
                category=source["category"],
                tags=source.get("tags") or [],
                source_type=source.get("source_type", "official_guideline"),
                source_grade=source.get("source_grade", "A"),
                license_value=source.get("license"),
                language=source.get("language", "en"),
                author_or_org=source.get("author_or_org"),
                refresh_policy=source.get("refresh_policy", "scheduled"),
                refresh_interval_hours=source.get("refresh_interval_hours"),
                catalog_key=source.get("key"),
                catalog_file=str(catalog_path),
            )
            results.append({"key": source.get("key"), "url": source["url"], **result})
    print(json.dumps({"catalog": str(catalog_path), "results": results}, ensure_ascii=False, indent=2))


async def _catalog_plan(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGCatalogControlService(db, settings).create_plan(
            catalog_file=args.file,
            report_path=args.report_path,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _catalog_runs(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGCatalogControlService(db, settings).list_runs(limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _catalog_run(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGCatalogControlService(db, settings).get_run(args.run_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _catalog_apply(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGCatalogControlService(db, settings).apply_run(run_id=args.run_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _refresh_source(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGService(db, settings).refresh_source(
            args.source_id,
            force=args.force,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _refresh_due(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGService(db, settings).refresh_due(limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _decisions(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGService(db, settings).list_decisions(
            job_id=args.job_id,
            limit=args.limit,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


async def _reindex(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGService(db, settings).reindex(source_id=args.source_id)
    print(f"Reindex finished: indexed={result['indexed']} failed={result['failed']}")


async def _archive(args: argparse.Namespace) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await RAGService(db, settings).archive_source(args.source_id)
    print(f"Archived sources={result['sources']} chunks={result['chunks']}")


async def _evaluate(args: argparse.Namespace) -> None:
    settings = get_settings()
    cases = load_retrieval_cases(args.cases)
    async with AsyncSessionLocal() as db:
        result = await evaluate_retrieval(
            RAGService(db, settings),
            cases,
            top_k=args.top_k,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.report_path:
        _write_evaluation_report(result, Path(args.report_path))
    if result["failed"]:
        raise SystemExit(1)


async def _validate_v1(args: argparse.Namespace) -> None:
    settings = get_settings()
    cases = load_retrieval_cases(args.cases)
    async with AsyncSessionLocal() as db:
        service = RAGService(db, settings)
        evaluation = await evaluate_retrieval(service, cases, top_k=args.top_k)
        db_counts = await _load_v1_db_counts(db)
        url_source_summary = await _load_v1_url_source_summary(db)
        decision_summary = await _load_v1_decision_summary(db)
        recent_jobs = await _load_v1_recent_jobs(db, limit=args.job_limit)
        latest_catalog_plan = await _load_latest_catalog_plan(db)
        try:
            index_status = await service.index_status()
        except Exception as exc:  # pragma: no cover - depends on local OpenSearch availability
            index_status = {
                "index": settings.RAG_OPENSEARCH_INDEX,
                "alias": settings.RAG_OPENSEARCH_ALIAS,
                "exists": False,
                "alias_exists": False,
                "error": str(exc),
            }

    report = {
        "evaluation": evaluation,
        "db_counts": db_counts,
        "url_source_summary": url_source_summary,
        "decision_summary": decision_summary,
        "recent_jobs": recent_jobs,
        "latest_catalog_plan": latest_catalog_plan,
        "index_status": index_status,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.report_path:
        _write_v1_validation_report(report, Path(args.report_path))
    if evaluation["failed"]:
        raise SystemExit(1)


async def _load_v1_db_counts(db) -> dict[str, int]:
    rows = (
        await db.execute(
            text(
                """
                SELECT 'rag_sources' AS name, count(*)::int AS value FROM rag_sources
                UNION ALL SELECT 'rag_chunks', count(*)::int FROM rag_chunks
                UNION ALL SELECT 'rag_chunks_active', count(*)::int FROM rag_chunks WHERE status = 'active'
                UNION ALL SELECT 'rag_ingest_jobs', count(*)::int FROM rag_ingest_jobs
                UNION ALL SELECT 'rag_pipeline_decisions', count(*)::int FROM rag_pipeline_decisions
                UNION ALL SELECT 'rag_embedding_cache', count(*)::int FROM rag_embedding_cache
                UNION ALL SELECT 'rag_catalog_plan_runs', count(*)::int FROM rag_catalog_plan_runs
                UNION ALL SELECT 'rag_catalog_plan_items', count(*)::int FROM rag_catalog_plan_items
                ORDER BY name
                """
            )
        )
    ).mappings().all()
    return {str(row["name"]): int(row["value"]) for row in rows}


async def _load_v1_url_source_summary(db) -> dict[str, Any]:
    row = (
        await db.execute(
            text(
                """
                SELECT
                  count(*) FILTER (WHERE origin_type = 'url_html')::int AS url_source_count,
                  count(*) FILTER (WHERE origin_type IN ('file_markdown', 'file_text', 'file_pdf'))::int AS local_file_source_count,
                  count(*) FILTER (WHERE origin_type = 'url_html' AND metadata ? 'fetch_metadata'
                    AND metadata->'fetch_metadata' ? 'catalog_key')::int AS catalog_source_count,
                  count(*) FILTER (WHERE origin_type IN ('file_markdown', 'file_text', 'file_pdf') AND metadata ? 'fetch_metadata'
                    AND metadata->'fetch_metadata' ? 'catalog_key')::int AS catalog_local_file_source_count,
                  count(*) FILTER (WHERE parser_type = 'html')::int AS html_parser_source_count,
                  count(*) FILTER (WHERE parser_type = 'markdown')::int AS markdown_parser_source_count,
                  count(*) FILTER (WHERE parser_type = 'text')::int AS text_parser_source_count,
                  count(*) FILTER (WHERE parser_type = 'pdf_text')::int AS pdf_text_parser_source_count,
                  count(*) FILTER (WHERE source_grade = 'A')::int AS source_grade_a_count,
                  count(*) FILTER (WHERE origin_type = 'url_html' AND external_etag IS NOT NULL)::int AS etag_present_count,
                  count(*) FILTER (WHERE origin_type = 'url_html' AND external_last_modified IS NOT NULL)::int AS last_modified_present_count,
                  count(*) FILTER (WHERE origin_type IN ('file_markdown', 'file_text', 'file_pdf') AND metadata ? 'fetch_metadata'
                    AND metadata->'fetch_metadata' ? 'file_size')::int AS local_file_fingerprint_count,
                  count(*) FILTER (WHERE origin_type = 'url_html' AND next_refresh_at IS NOT NULL)::int AS scheduled_refresh_count,
                  count(*) FILTER (WHERE origin_type = 'url_html' AND next_refresh_at <= now())::int AS stale_source_count
                FROM rag_sources
                """
            )
        )
    ).mappings().one()
    return {
        "url_source_count": int(row["url_source_count"]),
        "local_file_source_count": int(row["local_file_source_count"]),
        "catalog_source_count": int(row["catalog_source_count"]),
        "catalog_local_file_source_count": int(row["catalog_local_file_source_count"]),
        "html_parser_source_count": int(row["html_parser_source_count"]),
        "markdown_parser_source_count": int(row["markdown_parser_source_count"]),
        "text_parser_source_count": int(row["text_parser_source_count"]),
        "pdf_text_parser_source_count": int(row["pdf_text_parser_source_count"]),
        "source_grade_a_count": int(row["source_grade_a_count"]),
        "etag_present_count": int(row["etag_present_count"]),
        "last_modified_present_count": int(row["last_modified_present_count"]),
        "local_file_fingerprint_count": int(row["local_file_fingerprint_count"]),
        "scheduled_refresh_count": int(row["scheduled_refresh_count"]),
        "stale_source_count": int(row["stale_source_count"]),
    }


async def _load_v1_decision_summary(db) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text(
                """
                SELECT selected_action, reason_code, count(*)::int AS count
                FROM rag_pipeline_decisions
                GROUP BY selected_action, reason_code
                ORDER BY selected_action, reason_code
                """
            )
        )
    ).mappings().all()
    return [
        {
            "selected_action": str(row["selected_action"]),
            "reason_code": str(row["reason_code"]),
            "count": int(row["count"]),
        }
        for row in rows
    ]


async def _load_v1_recent_jobs(db, *, limit: int) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text(
                """
                SELECT id, job_type, source_id, status, pipeline_stage, skipped_reason,
                       coalesce(change_ratio, 0.0) AS change_ratio,
                       chunks_total, chunks_succeeded, embedding_reuse_count,
                       reembedding_count, index_skip_count
                FROM rag_ingest_jobs
                ORDER BY id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
    ).mappings().all()
    return [
        {
            "id": int(row["id"]),
            "job_type": str(row["job_type"]),
            "source_id": int(row["source_id"]) if row["source_id"] is not None else None,
            "status": str(row["status"]),
            "pipeline_stage": str(row["pipeline_stage"]),
            "skipped_reason": str(row["skipped_reason"]) if row["skipped_reason"] else None,
            "change_ratio": float(row["change_ratio"]),
            "chunks_total": int(row["chunks_total"]),
            "chunks_succeeded": int(row["chunks_succeeded"]),
            "embedding_reuse_count": int(row["embedding_reuse_count"]),
            "reembedding_count": int(row["reembedding_count"]),
            "index_skip_count": int(row["index_skip_count"]),
        }
        for row in rows
    ]


async def _load_latest_catalog_plan(db) -> dict[str, Any] | None:
    row = (
        await db.execute(
            text(
                """
                SELECT id, status, total_sources, planned_create_count, planned_skip_count,
                       planned_partial_count, planned_full_count, planned_manual_count,
                       planned_defer_count, created_at
                FROM rag_catalog_plan_runs
                ORDER BY id DESC
                LIMIT 1
                """
            )
        )
    ).mappings().first()
    if not row:
        return None
    result = dict(row)
    if result.get("created_at") is not None:
        result["created_at"] = result["created_at"].isoformat()
    return result


def _write_evaluation_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# RAG Retrieval Evaluation Report",
        "",
        "## Summary",
        "",
        f"- total: {result['total']}",
        f"- passed: {result['passed']}",
        f"- failed: {result['failed']}",
        f"- pass_rate: {result['pass_rate']:.2%}",
        f"- fallback_count: {result.get('fallback_count', 0)}",
        f"- safety_source_hit_count: {result.get('safety_source_hit_count', 0)}",
        f"- source_grade_hit_count: {result.get('source_grade_hit_count', 0)}",
        "",
        "## Cases",
        "",
    ]
    for item in result.get("results", []):
        lines.extend(
            [
                f"### {item['query']}",
                "",
                f"- passed: {item['passed']}",
                f"- category_matched: {item['category_matched']}",
                f"- tag_matched: {item['tag_matched']}",
                f"- source_matched: {item['source_matched']}",
                f"- fallback_used: {item.get('fallback_used', False)}",
                f"- top_titles: {', '.join(item.get('top_titles', []))}",
                "",
            ]
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def _write_v1_validation_report(report: dict[str, Any], report_path: Path) -> None:
    evaluation = report["evaluation"]
    index_status = report.get("index_status", {})
    lines = [
        "# RAG v1 운영 검증 리포트",
        "",
        "> 이 문서는 `python -m app.cli.rag validate-v1` 명령으로 재생성 가능한 운영 검증 리포트다.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "docker compose exec backend python -m app.cli.rag validate-v1 --report-path /workspace/docs/RAG_EVALUATION_REPORT.md",
        "```",
        "",
        "## Coverage",
        "",
        "- Markdown seed corpus ingest 이후의 운영 DB와 OpenSearch index 상태를 검증한다.",
        "- Retrieval evaluation, source grade hit, safety source hit, fallback count를 기록한다.",
        "- Skip/partial/full refresh decision trace는 `rag_pipeline_decisions`와 recent job metrics로 확인한다.",
        "- Text/PDF parser capability는 backend tests에서 file path 기반 fixture로 검증한다.",
        "",
        "## Summary",
        "",
        f"- total_cases: {evaluation['total']}",
        f"- passed: {evaluation['passed']}",
        f"- failed: {evaluation['failed']}",
        f"- pass_rate: {evaluation['pass_rate']:.2%}",
        f"- fallback_count: {evaluation.get('fallback_count', 0)}",
        f"- safety_source_hit_count: {evaluation.get('safety_source_hit_count', 0)}",
        f"- source_grade_hit_count: {evaluation.get('source_grade_hit_count', 0)}",
        "",
        "## OpenSearch Index",
        "",
        "| Field | Value |",
        "|-------|-------|",
    ]
    for key in [
        "index",
        "alias",
        "exists",
        "alias_exists",
        "health",
        "status",
        "docs_count",
        "docs_deleted",
        "store_size",
        "primary_store_size",
        "error",
    ]:
        if key in index_status:
            lines.append(f"| `{key}` | {_markdown_value(index_status.get(key))} |")

    lines.extend(
        [
            "",
            "## DB Counts",
            "",
            "| Metric | Count |",
            "|--------|-------|",
        ]
    )
    for name, count in sorted((report.get("db_counts") or {}).items()):
        lines.append(f"| `{name}` | {count} |")

    lines.extend(
        [
            "",
            "## Source Acquisition Summary",
            "",
            "| Metric | Count |",
            "|--------|-------|",
        ]
    )
    for name, count in sorted((report.get("url_source_summary") or {}).items()):
        lines.append(f"| `{name}` | {count} |")

    latest_catalog_plan = report.get("latest_catalog_plan")
    if latest_catalog_plan:
        lines.extend(
            [
                "",
                "## Latest Catalog Plan",
                "",
                "| Field | Value |",
                "|-------|-------|",
            ]
        )
        for name, value in latest_catalog_plan.items():
            lines.append(f"| `{name}` | {_markdown_value(value)} |")

    lines.extend(
        [
            "",
            "## Decision Summary",
            "",
            "| Action | Reason | Count |",
            "|--------|--------|-------|",
        ]
    )
    for item in report.get("decision_summary", []):
        lines.append(
            "| `{selected_action}` | `{reason_code}` | {count} |".format(**item)
        )

    lines.extend(
        [
            "",
            "## Recent Jobs",
            "",
            "| Job | Type | Source | Status | Stage | Change Ratio | Reuse | Reembed | Index Skip |",
            "|-----|------|--------|--------|-------|--------------|-------|---------|------------|",
        ]
    )
    for job in report.get("recent_jobs", []):
        source_id = job["source_id"] if job["source_id"] is not None else ""
        job_row = {**job, "source_id": source_id}
        lines.append(
            "| {id} | {job_type} | {source_id} | {status} | {pipeline_stage} | {change_ratio:.4f} | "
            "{embedding_reuse_count} | {reembedding_count} | {index_skip_count} |".format(
                **job_row,
            )
        )

    lines.extend(
        [
            "",
            "## Retrieval Cases",
            "",
            "| Query | Passed | Category | Tag | Source | Fallback | Top Titles |",
            "|-------|--------|----------|-----|--------|----------|------------|",
        ]
    )
    for item in evaluation.get("results", []):
        top_titles = ", ".join(item.get("top_titles", []))
        lines.append(
            "| {query} | {passed} | {category_matched} | {tag_matched} | {source_matched} | "
            "{fallback_used} | {top_titles} |".format(
                query=_escape_table_value(item["query"]),
                passed=item["passed"],
                category_matched=item["category_matched"],
                tag_matched=item["tag_matched"],
                source_matched=item["source_matched"],
                fallback_used=item.get("fallback_used", False),
                top_titles=_escape_table_value(top_titles),
            )
        )

    lines.extend(
        [
            "",
            "## V1 Verdict",
            "",
            "- Markdown seed corpus ingest, OpenSearch retrieval, decision trace, evaluation report 재생성을 검증한다.",
            "- Text/PDF parser capability는 backend tests에서 file path 기반 fixture로 검증한다.",
            "- OpenSearch 장애 fallback은 automated test와 policy trace 기준으로 검증한다.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def _markdown_value(value: Any) -> str:
    return _escape_table_value("" if value is None else str(value))


def _escape_table_value(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RAG KnowledgeOps CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ensure-index", help="Create OpenSearch RAG index and alias if missing")
    subparsers.add_parser("delete-index", help="Delete the configured OpenSearch RAG index")

    preview = subparsers.add_parser("parse-preview", help="Preview parser/chunker output without persisting")
    preview.add_argument("--file", required=True, help="Document path")
    preview.add_argument("--parser", default="auto", help="auto, markdown, text, pdf_text")

    fetch_preview = subparsers.add_parser("fetch-preview", help="Preview single-page URL acquisition and HTML chunking")
    fetch_preview.add_argument("--url", required=True, help="Official source URL")
    fetch_preview.add_argument("--title", default=None, help="Optional title override")

    ingest = subparsers.add_parser("ingest", help="Ingest a markdown/text document into RAG v2")
    ingest.add_argument("--file", required=True, help="Document path")
    ingest.add_argument("--title", required=True, help="Source title")
    ingest.add_argument("--category", required=True, help="RAG category")
    ingest.add_argument("--tags", default="", help="Comma-separated tags")
    ingest.add_argument("--source-url", default="", help="Original source URL")
    ingest.add_argument("--source-type", default="internal_policy", help="Source type")
    ingest.add_argument("--source-grade", default="B", help="Source trust grade")
    ingest.add_argument("--license", default="internal-summary", help="License or usage note")
    ingest.add_argument("--language", default="ko", help="Document language")
    ingest.add_argument("--author-or-org", default=None, help="Author or organization")

    register = subparsers.add_parser("register-source", help="Register and ingest a refreshable RAG source")
    register.add_argument("--file", "--origin-uri", dest="file", required=True, help="Document path")
    register.add_argument("--title", default=None, help="Source title")
    register.add_argument("--category", required=True, help="RAG category")
    register.add_argument("--tags", default="", help="Comma-separated tags")
    register.add_argument("--parser", default="auto", help="auto, markdown, text, pdf_text")
    register.add_argument("--source-url", default="", help="Original source URL")
    register.add_argument("--source-type", default="file", help="Source type")
    register.add_argument("--source-grade", default="B", help="Source trust grade")
    register.add_argument("--license", default="internal-summary", help="License or usage note")
    register.add_argument("--language", default="ko", help="Document language")
    register.add_argument("--author-or-org", default=None, help="Author or organization")
    register.add_argument("--refresh-policy", default="manual", choices=["manual", "scheduled", "never"], help="Refresh policy")
    register.add_argument("--refresh-interval-hours", type=int, default=None, help="Scheduled refresh interval")

    register_url = subparsers.add_parser("register-url", help="Register and ingest a single official URL source")
    register_url.add_argument("--url", required=True, help="Official source URL")
    register_url.add_argument("--title", default=None, help="Source title")
    register_url.add_argument("--category", required=True, help="RAG category")
    register_url.add_argument("--tags", default="", help="Comma-separated tags")
    register_url.add_argument("--source-type", default="official_guideline", help="Source type")
    register_url.add_argument("--source-grade", default="A", help="Source trust grade")
    register_url.add_argument("--license", default=None, help="License or usage note")
    register_url.add_argument("--language", default="en", help="Document language")
    register_url.add_argument("--author-or-org", default=None, help="Author or organization")
    register_url.add_argument("--refresh-policy", default="scheduled", choices=["manual", "scheduled", "never"], help="Refresh policy")
    register_url.add_argument("--refresh-interval-hours", type=int, default=720, help="Scheduled refresh interval")

    ingest_catalog = subparsers.add_parser("ingest-catalog", help="Ingest official URL sources from a catalog JSON file")
    ingest_catalog.add_argument("--file", required=True, help="Catalog JSON path")

    catalog_plan = subparsers.add_parser("catalog-plan", help="Create a persisted live-fetch catalog refresh plan")
    catalog_plan.add_argument("--file", required=True, help="Catalog JSON path")
    catalog_plan.add_argument("--report-path", default=None, help="Optional markdown report output path")

    catalog_runs = subparsers.add_parser("catalog-runs", help="List persisted catalog plan runs")
    catalog_runs.add_argument("--limit", type=int, default=20, help="Maximum runs to show")

    catalog_run = subparsers.add_parser("catalog-run", help="Show one persisted catalog plan run")
    catalog_run.add_argument("--run-id", type=int, required=True, help="Catalog plan run id")

    catalog_apply = subparsers.add_parser("catalog-apply", help="Apply a persisted catalog plan run")
    catalog_apply.add_argument("--run-id", type=int, required=True, help="Catalog plan run id")

    refresh_source = subparsers.add_parser("refresh-source", help="Refresh a registered source by source id")
    refresh_source.add_argument("--source-id", type=int, required=True, help="Source id")
    refresh_source.add_argument("--force", action="store_true", help="Refresh even when source hash is unchanged")

    refresh_due = subparsers.add_parser("refresh-due", help="Refresh scheduled sources whose next_refresh_at is due")
    refresh_due.add_argument("--limit", type=int, default=20, help="Maximum sources to refresh")

    reindex = subparsers.add_parser("reindex", help="Reindex active chunks into OpenSearch")
    reindex.add_argument("--source-id", type=int, default=None, help="Optional source id")

    archive = subparsers.add_parser("archive", help="Archive a RAG source and remove its indexed chunks")
    archive.add_argument("--source-id", type=int, required=True, help="Source id")

    evaluate = subparsers.add_parser("evaluate", help="Run retrieval evaluation cases against RAG search")
    evaluate.add_argument("--cases", default=str(DEFAULT_EVAL_CASES_PATH), help="Evaluation cases JSON path")
    evaluate.add_argument("--top-k", type=int, default=3, help="Number of retrieval results per case")
    evaluate.add_argument("--report-path", default=None, help="Optional markdown report output path")

    validate_v1 = subparsers.add_parser("validate-v1", help="Run RAG v1 operational validation and write a report")
    validate_v1.add_argument("--cases", default=str(DEFAULT_EVAL_CASES_PATH), help="Evaluation cases JSON path")
    validate_v1.add_argument("--top-k", type=int, default=3, help="Number of retrieval results per case")
    validate_v1.add_argument("--job-limit", type=int, default=10, help="Number of recent ingest jobs in the report")
    validate_v1.add_argument("--report-path", default=None, help="Optional markdown report output path")

    decisions = subparsers.add_parser("decisions", help="Show RAG pipeline policy decisions")
    decisions.add_argument("--job-id", type=int, default=None, help="Optional ingest job id")
    decisions.add_argument("--limit", type=int, default=20, help="Maximum decisions to show")

    return parser


async def _main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ensure-index":
        await _ensure_index()
    elif args.command == "delete-index":
        await _delete_index()
    elif args.command == "parse-preview":
        await _parse_preview(args)
    elif args.command == "fetch-preview":
        await _fetch_preview(args)
    elif args.command == "ingest":
        await _ingest(args)
    elif args.command == "register-source":
        await _register_source(args)
    elif args.command == "register-url":
        await _register_url(args)
    elif args.command == "ingest-catalog":
        await _ingest_catalog(args)
    elif args.command == "catalog-plan":
        await _catalog_plan(args)
    elif args.command == "catalog-runs":
        await _catalog_runs(args)
    elif args.command == "catalog-run":
        await _catalog_run(args)
    elif args.command == "catalog-apply":
        await _catalog_apply(args)
    elif args.command == "refresh-source":
        await _refresh_source(args)
    elif args.command == "refresh-due":
        await _refresh_due(args)
    elif args.command == "reindex":
        await _reindex(args)
    elif args.command == "archive":
        await _archive(args)
    elif args.command == "evaluate":
        await _evaluate(args)
    elif args.command == "validate-v1":
        await _validate_v1(args)
    elif args.command == "decisions":
        await _decisions(args)
    else:
        parser.error(f"Unsupported command: {args.command}")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
