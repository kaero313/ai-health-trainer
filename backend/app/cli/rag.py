from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.services.rag_service import RAGService


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RAG KnowledgeOps CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ensure-index", help="Create OpenSearch RAG index and alias if missing")
    subparsers.add_parser("delete-index", help="Delete the configured OpenSearch RAG index")

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

    reindex = subparsers.add_parser("reindex", help="Reindex active chunks into OpenSearch")
    reindex.add_argument("--source-id", type=int, default=None, help="Optional source id")

    archive = subparsers.add_parser("archive", help="Archive a RAG source and remove its indexed chunks")
    archive.add_argument("--source-id", type=int, required=True, help="Source id")

    return parser


async def _main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ensure-index":
        await _ensure_index()
    elif args.command == "delete-index":
        await _delete_index()
    elif args.command == "ingest":
        await _ingest(args)
    elif args.command == "reindex":
        await _reindex(args)
    elif args.command == "archive":
        await _archive(args)
    else:
        parser.error(f"Unsupported command: {args.command}")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
