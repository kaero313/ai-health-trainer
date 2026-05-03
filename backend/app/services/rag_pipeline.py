from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

try:
    from pypdf import PdfReader
except ModuleNotFoundError:  # pragma: no cover - optional until PDF ingest is used
    PdfReader = None  # type: ignore[assignment]

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:  # pragma: no cover - optional until HTML ingest is used
    BeautifulSoup = None  # type: ignore[assignment]


NORMALIZATION_VERSION = "chunk-normalize-v1"
CHUNKER_VERSION = "structure-chunker-v2"
POLICY_VERSION = "rag-policy-v1"
HASH_SCHEMA_VERSION = 1
METADATA_SCHEMA_VERSION = 1
DEFAULT_MIN_CHUNK_CHARS = 80
DEFAULT_MAX_CHUNK_CHARS = 1200


PARSER_VERSIONS = {
    "markdown": "markdown-parser-v1",
    "text": "text-parser-v1",
    "pdf_text": "pdf-text-parser-v1",
    "html": "html-parser-v1",
}


@dataclass(frozen=True)
class ParsedSection:
    title: str
    text: str
    section_path: list[str]
    page_number: int | None = None
    paragraph_range: tuple[int, int] | None = None
    char_range: tuple[int, int] | None = None
    parent_heading_path: list[str] | None = None
    parent_section_hash: str | None = None
    source_anchor: str | None = None
    source_url: str | None = None
    source_content_type: str | None = None


@dataclass(frozen=True)
class ParsedDocument:
    title: str
    source_uri: str | None
    parser_type: str
    parser_version: str
    parser_confidence: float
    content_hash: str
    raw_content_hash: str
    normalized_content: str
    sections: list[ParsedSection]
    skipped_sections: int = 0
    fetch_metadata: dict[str, Any] | None = None


class SourceMetadata(BaseModel):
    metadata_schema_version: int = METADATA_SCHEMA_VERSION
    hash_schema_version: int = HASH_SCHEMA_VERSION
    parser_type: str
    parser_version: str
    chunker_version: str = CHUNKER_VERSION
    normalization_version: str = NORMALIZATION_VERSION
    raw_content_hash: str
    normalized_content_hash: str
    parser_confidence: float
    skipped_sections: int = 0


class ChunkMetadata(BaseModel):
    metadata_schema_version: int = METADATA_SCHEMA_VERSION
    hash_schema_version: int = HASH_SCHEMA_VERSION
    parser_type: str
    parser_version: str
    chunker_version: str = CHUNKER_VERSION
    normalization_version: str = NORMALIZATION_VERSION
    section_path: list[str] = Field(default_factory=list)
    page_number: int | None = None
    paragraph_range: list[int] | None = None
    char_range: list[int] | None = None
    split_reason: str | None = None
    merge_reason: str | None = None
    anchor_inputs: dict[str, Any] = Field(default_factory=dict)
    embedding_reuse: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class ChunkPlan:
    chunk_index: int
    title: str
    content: str
    content_hash: str
    anchor_hash: str
    embedding_input_hash: str
    index_payload_hash: str
    chunk_strategy: str
    chunk_anchor: str
    page_number: int | None
    token_count: int
    metadata: dict[str, Any]


@dataclass(frozen=True)
class PipelineDecision:
    decision_type: str
    selected_action: str
    risk_level: str
    reason_code: str
    context: dict[str, Any]
    tradeoffs: dict[str, Any]
    policy_version: str = POLICY_VERSION


class RAGDocumentParser:
    def parse_file(self, file_path: str | Path, parser_type: str = "auto") -> ParsedDocument:
        path = Path(file_path)
        selected_parser = self.detect_parser(path, parser_type)
        if selected_parser == "pdf_text":
            return self._parse_pdf(path)

        content = path.read_text(encoding="utf-8")
        if selected_parser == "markdown":
            return self.parse_markdown(content, title=path.stem, source_uri=str(path))
        return self.parse_text(content, title=path.stem, source_uri=str(path))

    def parse_content(
        self,
        content: str,
        *,
        title: str,
        source_uri: str | None = None,
        parser_type: str = "text",
    ) -> ParsedDocument:
        if parser_type == "markdown":
            return self.parse_markdown(content, title=title, source_uri=source_uri)
        return self.parse_text(content, title=title, source_uri=source_uri)

    @staticmethod
    def detect_parser(path: Path, parser_type: str = "auto") -> str:
        if parser_type != "auto":
            return parser_type
        suffix = path.suffix.lower()
        if suffix in {".md", ".markdown"}:
            return "markdown"
        if suffix == ".pdf":
            return "pdf_text"
        return "text"

    def parse_markdown(self, content: str, *, title: str, source_uri: str | None = None) -> ParsedDocument:
        raw_hash = hash_text(content)
        normalized = normalize_text(content)
        sections: list[ParsedSection] = []
        heading_stack: list[str] = []
        current_title = title
        current_path = ["Document"]
        current_lines: list[str] = []
        char_start = 0
        cursor = 0

        def flush(char_end: int) -> None:
            body = "\n".join(current_lines).strip()
            if not body:
                return
            section_title = " > ".join(current_path) if current_path else current_title
            section_text = f"{section_title}\n\n{body}" if section_title else body
            sections.append(
                ParsedSection(
                    title=current_title,
                    text=section_text,
                    section_path=list(current_path),
                    char_range=(char_start, char_end),
                )
            )

        for line in content.splitlines():
            match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if match:
                flush(cursor)
                level = len(match.group(1))
                heading = match.group(2).strip()
                heading_stack = heading_stack[: level - 1] + [heading]
                current_title = heading
                current_path = heading_stack.copy()
                current_lines = []
                char_start = cursor
            else:
                current_lines.append(line)
            cursor += len(line) + 1
        flush(cursor)

        if not sections and normalized:
            sections.append(
                ParsedSection(
                    title=title,
                    text=normalized,
                    section_path=["Document"],
                    char_range=(0, len(content)),
                )
            )

        return ParsedDocument(
            title=title,
            source_uri=source_uri,
            parser_type="markdown",
            parser_version=PARSER_VERSIONS["markdown"],
            parser_confidence=0.95 if sections else 0.0,
            content_hash=hash_text(normalized),
            raw_content_hash=raw_hash,
            normalized_content=normalized,
            sections=sections,
        )

    def parse_text(self, content: str, *, title: str, source_uri: str | None = None) -> ParsedDocument:
        raw_hash = hash_text(content)
        normalized = normalize_text(content)
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", content) if paragraph.strip()]
        sections: list[ParsedSection] = []
        cursor = 0
        for idx, paragraph in enumerate(paragraphs, start=1):
            start = content.find(paragraph, cursor)
            end = start + len(paragraph) if start >= 0 else cursor + len(paragraph)
            cursor = max(end, cursor)
            sections.append(
                ParsedSection(
                    title=f"{title} paragraph {idx}",
                    text=paragraph,
                    section_path=["Document"],
                    paragraph_range=(idx, idx),
                    char_range=(start if start >= 0 else None, end) if start >= 0 else None,
                )
            )

        if not sections and normalized:
            sections.append(ParsedSection(title=title, text=normalized, section_path=["Document"]))

        return ParsedDocument(
            title=title,
            source_uri=source_uri,
            parser_type="text",
            parser_version=PARSER_VERSIONS["text"],
            parser_confidence=0.90 if sections else 0.0,
            content_hash=hash_text(normalized),
            raw_content_hash=raw_hash,
            normalized_content=normalized,
            sections=sections,
        )

    def parse_html(
        self,
        content: str,
        *,
        title: str | None = None,
        source_uri: str | None = None,
        source_url: str | None = None,
        content_type: str | None = None,
        fetch_metadata: dict[str, Any] | None = None,
    ) -> ParsedDocument:
        if BeautifulSoup is None:
            raise ValueError("beautifulsoup4 is required for html parsing")

        raw_hash = hash_text(content)
        soup = BeautifulSoup(content, "html.parser")
        html_title = self._html_title(soup)
        document_title = title or html_title or source_uri or "HTML source"

        for selector in ["script", "style", "noscript", "nav", "footer", "header", "svg"]:
            for node in soup.select(selector):
                node.decompose()

        root = soup.find("main") or soup.find("article") or soup.body or soup
        parent_records: list[dict[str, Any]] = []
        heading_stack: list[str] = ["Document"]
        current_children: list[str] = []
        current_heading_seen = False
        skip_current_parent = False
        paragraph_counter = 1
        skipped = 0

        def flush_parent() -> None:
            nonlocal current_children
            normalized_children = [normalize_text(child) for child in current_children if normalize_text(child)]
            if normalized_children:
                parent_records.append(
                    {
                        "heading_path": list(heading_stack),
                        "children": normalized_children,
                        "heading_seen": current_heading_seen,
                    }
                )
            current_children = []

        for element in root.find_all(["h1", "h2", "h3", "p", "li", "tr"], recursive=True):
            name = str(element.name or "").lower()
            if name in {"h1", "h2", "h3"}:
                heading = self._html_clean_text(element.get_text(" ", strip=True))
                if not heading:
                    continue
                flush_parent()
                skip_current_parent = self._is_html_boilerplate_heading(heading)
                level = int(name[1])
                if heading_stack == ["Document"]:
                    heading_stack = []
                heading_stack = heading_stack[: level - 1] + [heading]
                current_heading_seen = True
                continue

            if skip_current_parent:
                skipped += 1
                continue
            if name in {"p", "li"} and element.find_parent("tr") is not None:
                continue
            if name == "p" and element.find_parent("li") is not None:
                continue
            if name == "tr":
                cells = [
                    self._html_clean_text(cell.get_text(" ", strip=True))
                    for cell in element.find_all(["th", "td"], recursive=False)
                ]
                text_value = " | ".join(cell for cell in cells if cell)
            else:
                text_value = self._html_clean_text(element.get_text(" ", strip=True))

            if text_value and not self._is_html_boilerplate_text(text_value):
                current_children.append(text_value)
            else:
                skipped += 1
        flush_parent()

        sections: list[ParsedSection] = []
        all_section_texts: list[str] = []
        parent_hashes: list[str] = []
        for parent_index, record in enumerate(parent_records, start=1):
            heading_path = record["heading_path"] or ["Document"]
            parent_text = "\n\n".join(record["children"])
            parent_hash = hash_json(
                {
                    "source_uri": source_uri,
                    "source_url": source_url,
                    "heading_path": heading_path,
                    "parent_text_hash": hash_text(parent_text),
                }
            )
            parent_hashes.append(parent_hash)
            parent_anchor = self._html_anchor(heading_path, parent_index)
            heading_label = " > ".join(heading_path)
            for child in record["children"]:
                child_text = f"{heading_label}\n\n{child}" if heading_label else child
                sections.append(
                    ParsedSection(
                        title=heading_path[-1] if heading_path else document_title,
                        text=child_text,
                        section_path=list(heading_path),
                        paragraph_range=(paragraph_counter, paragraph_counter),
                        parent_heading_path=list(heading_path),
                        parent_section_hash=parent_hash,
                        source_anchor=parent_anchor,
                        source_url=source_url,
                        source_content_type=content_type,
                    )
                )
                all_section_texts.append(child_text)
                paragraph_counter += 1

        normalized_content = normalize_text("\n\n".join(all_section_texts))
        parser_confidence = self._html_confidence(
            sections=sections,
            normalized_content=normalized_content,
            heading_count=sum(1 for record in parent_records if record.get("heading_seen")),
        )
        metadata = dict(fetch_metadata or {})
        metadata["parent_section_hashes"] = parent_hashes
        metadata["parent_section_count"] = len(parent_hashes)

        return ParsedDocument(
            title=document_title,
            source_uri=source_uri,
            parser_type="html",
            parser_version=PARSER_VERSIONS["html"],
            parser_confidence=parser_confidence,
            content_hash=hash_text(normalized_content),
            raw_content_hash=raw_hash,
            normalized_content=normalized_content,
            sections=sections,
            skipped_sections=skipped,
            fetch_metadata=metadata,
        )

    def _parse_pdf(self, path: Path) -> ParsedDocument:
        if PdfReader is None:
            raise ValueError("pypdf is required for pdf_text parsing")

        reader = PdfReader(str(path))
        sections: list[ParsedSection] = []
        skipped = 0
        all_text: list[str] = []
        paragraph_counter = 1
        for page_index, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            normalized_page = normalize_text(page_text)
            if not normalized_page:
                skipped += 1
                continue
            all_text.append(normalized_page)
            paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", page_text) if paragraph.strip()]
            if not paragraphs:
                paragraphs = [normalized_page]
            for paragraph in paragraphs:
                sections.append(
                    ParsedSection(
                        title=f"{path.stem} page {page_index}",
                        text=paragraph,
                        section_path=[f"page:{page_index}"],
                        page_number=page_index,
                        paragraph_range=(paragraph_counter, paragraph_counter),
                    )
                )
                paragraph_counter += 1

        content = "\n\n".join(all_text)
        non_empty_ratio = len(all_text) / len(reader.pages) if reader.pages else 0.0
        confidence = 0.0 if not sections else min(0.95, 0.55 + (0.40 * non_empty_ratio))
        return ParsedDocument(
            title=path.stem,
            source_uri=str(path),
            parser_type="pdf_text",
            parser_version=PARSER_VERSIONS["pdf_text"],
            parser_confidence=confidence,
            content_hash=hash_text(content),
            raw_content_hash=hash_text(path.read_bytes()),
            normalized_content=content,
            sections=sections,
            skipped_sections=skipped,
        )

    @staticmethod
    def _html_title(soup: Any) -> str | None:
        title_node = soup.find("title")
        if title_node:
            title = RAGDocumentParser._html_clean_text(title_node.get_text(" ", strip=True))
            if title:
                return title
        h1_node = soup.find("h1")
        if h1_node:
            title = RAGDocumentParser._html_clean_text(h1_node.get_text(" ", strip=True))
            if title:
                return title
        return None

    @staticmethod
    def _html_clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    @staticmethod
    def _html_anchor(heading_path: list[str], index: int) -> str:
        slug = "-".join(
            re.sub(r"[^a-z0-9]+", "-", item.lower()).strip("-")
            for item in heading_path
            if item.strip()
        )
        return slug[:180] or f"section-{index}"

    @staticmethod
    def _html_confidence(*, sections: list[ParsedSection], normalized_content: str, heading_count: int) -> float:
        if not sections:
            return 0.0
        if heading_count and len(normalized_content) >= 300:
            return 0.95
        if heading_count:
            return 0.82
        if len(normalized_content) >= 300:
            return 0.75
        return 0.55

    @staticmethod
    def _is_html_boilerplate_heading(value: str) -> bool:
        normalized = re.sub(r"\s+", " ", value or "").strip().lower()
        return normalized in {
            "on this page",
            "related pages",
            "related topics",
            "more information",
            "resources",
            "for more information",
        }

    @staticmethod
    def _is_html_boilerplate_text(value: str) -> bool:
        normalized = re.sub(r"\s+", " ", value or "").strip().lower()
        return normalized in {
            "top of page",
            "back to top",
            "return to top",
        }


class RAGChunkPlanner:
    def build_chunks(
        self,
        parsed: ParsedDocument,
        *,
        source_title: str,
        category: str,
        tags: list[str],
        source_grade: str,
        embedding_model: str,
        embedding_dim: int = 3072,
        source_version: int = 1,
        min_chars: int = DEFAULT_MIN_CHUNK_CHARS,
        max_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    ) -> list[ChunkPlan]:
        chunk_strategy = self._strategy_for_parser(parsed.parser_type)
        raw_chunks: list[tuple[ParsedSection, str, int, int, str | None]] = []
        for section in parsed.sections:
            normalized_section = normalize_text(section.text)
            if not normalized_section:
                continue
            parts = split_over_max(normalized_section, max_chars)
            for split_idx, part in enumerate(parts, start=1):
                split_reason = "max_chars" if len(parts) > 1 else None
                raw_chunks.append((section, part, split_idx, len(parts), split_reason))

        merged = self._merge_short_chunks(raw_chunks, min_chars, max_chars)
        plans: list[ChunkPlan] = []
        for idx, item in enumerate(merged, start=1):
            section, content, split_idx, split_total, split_reason, merge_reason = item
            content_hash = hash_text(content)
            anchor_inputs = {
                "source_uri": parsed.source_uri,
                "parser_type": parsed.parser_type,
                "chunk_strategy": chunk_strategy,
                "section_path": section.section_path,
                "page_number": section.page_number,
                "paragraph_range": list(section.paragraph_range) if section.paragraph_range else None,
                "split_index": split_idx if split_total > 1 else None,
            }
            anchor_hash = hash_json(anchor_inputs)
            embedding_input_hash = build_embedding_input_hash(
                content_hash=content_hash,
                embedding_model=embedding_model,
                embedding_dim=embedding_dim,
            )
            title = self._chunk_title(source_title, section, idx, len(merged))
            index_payload_hash = build_index_payload_hash(
                title=title,
                content_hash=content_hash,
                category=category,
                tags=tags,
                source_grade=source_grade,
                status="active",
                embedding_input_hash=embedding_input_hash,
                source_version=source_version,
            )
            metadata = ChunkMetadata(
                parser_type=parsed.parser_type,
                parser_version=parsed.parser_version,
                section_path=section.section_path,
                page_number=section.page_number,
                paragraph_range=list(section.paragraph_range) if section.paragraph_range else None,
                char_range=list(section.char_range) if section.char_range else None,
                split_reason=split_reason,
                merge_reason=merge_reason,
                anchor_inputs=anchor_inputs,
            ).model_dump(exclude_none=True)
            plans.append(
                ChunkPlan(
                    chunk_index=idx,
                    title=title,
                    content=content,
                    content_hash=content_hash,
                    anchor_hash=anchor_hash,
                    embedding_input_hash=embedding_input_hash,
                    index_payload_hash=index_payload_hash,
                    chunk_strategy=chunk_strategy,
                    chunk_anchor=json.dumps(anchor_inputs, ensure_ascii=False, sort_keys=True),
                    page_number=section.page_number,
                    token_count=estimate_token_count(content),
                    metadata=metadata,
                )
            )
        return plans

    @staticmethod
    def _strategy_for_parser(parser_type: str) -> str:
        if parser_type == "markdown":
            return "section"
        if parser_type == "pdf_text":
            return "page_paragraph"
        return "paragraph"

    @staticmethod
    def _chunk_title(source_title: str, section: ParsedSection, index: int, total: int) -> str:
        title = section.title or source_title
        return f"{title} ({index}/{total})"

    @staticmethod
    def _merge_short_chunks(
        chunks: list[tuple[ParsedSection, str, int, int, str | None]],
        min_chars: int,
        max_chars: int,
    ) -> list[tuple[ParsedSection, str, int, int, str | None, str | None]]:
        merged: list[tuple[ParsedSection, str, int, int, str | None, str | None]] = []
        for section, content, split_idx, split_total, split_reason in chunks:
            if len(content) >= min_chars or not merged:
                merged.append((section, content, split_idx, split_total, split_reason, None))
                continue
            prev_section, prev_content, prev_split_idx, prev_split_total, prev_split_reason, prev_merge_reason = merged[-1]
            candidate = f"{prev_content}\n\n{content}"
            if len(candidate) <= max_chars:
                merged[-1] = (
                    prev_section,
                    candidate,
                    prev_split_idx,
                    prev_split_total,
                    prev_split_reason,
                    prev_merge_reason or "short_chunk",
                )
            else:
                merged.append((section, content, split_idx, split_total, split_reason, None))
        return merged


class RAGDecisionPolicy:
    def choose_ingest_action(
        self,
        *,
        source_exists: bool,
        source_hash_same: bool,
        parser_confidence: float,
        change_ratio: float,
        parser_or_chunker_changed: bool,
        estimated_embedding_seconds: float,
        allowed_embedding_seconds: float,
        partial_refresh_threshold: float,
        parser_confidence_threshold: float,
        source_grade: str,
        category: str,
    ) -> PipelineDecision:
        context = {
            "source_exists": source_exists,
            "source_hash_same": source_hash_same,
            "parser_confidence": round(parser_confidence, 4),
            "change_ratio": round(change_ratio, 4),
            "parser_or_chunker_changed": parser_or_chunker_changed,
            "estimated_embedding_seconds": round(estimated_embedding_seconds, 4),
            "allowed_embedding_seconds": allowed_embedding_seconds,
            "partial_refresh_threshold": partial_refresh_threshold,
            "parser_confidence_threshold": parser_confidence_threshold,
            "source_grade": source_grade,
            "category": category,
        }

        if parser_confidence < parser_confidence_threshold:
            return PipelineDecision(
                decision_type="ingest_refresh",
                selected_action="manual_review_required",
                risk_level="high",
                reason_code="LOW_PARSER_CONFIDENCE",
                context=context,
                tradeoffs={
                    "accepted": "avoid low-confidence knowledge entering prompt context",
                    "rejected": "automatic ingest despite likely parser loss",
                },
            )
        if source_exists and source_hash_same:
            return PipelineDecision(
                decision_type="ingest_refresh",
                selected_action="skip_refresh",
                risk_level="low",
                reason_code="SOURCE_HASH_UNCHANGED",
                context=context,
                tradeoffs={
                    "accepted": "avoid unnecessary parsing, embedding, and indexing work",
                    "rejected": "forced reindex with no content change",
                },
            )
        if estimated_embedding_seconds > allowed_embedding_seconds:
            return PipelineDecision(
                decision_type="ingest_refresh",
                selected_action="defer_reembedding",
                risk_level="medium",
                reason_code="EMBEDDING_TIME_BUDGET_EXCEEDED",
                context=context,
                tradeoffs={
                    "accepted": "protect operational time budget and API quota",
                    "rejected": "blocking refresh until all embeddings complete",
                },
            )
        if not source_exists:
            return PipelineDecision(
                decision_type="ingest_refresh",
                selected_action="create_source",
                risk_level="medium" if source_grade in {"C", "D"} else "low",
                reason_code="NEW_SOURCE",
                context=context,
                tradeoffs={
                    "accepted": "new source is added with full traceability",
                    "rejected": "manual database-only seed without job lifecycle",
                },
            )
        if parser_or_chunker_changed or change_ratio >= partial_refresh_threshold:
            return PipelineDecision(
                decision_type="ingest_refresh",
                selected_action="full_reindex",
                risk_level="medium",
                reason_code="LARGE_OR_STRUCTURAL_CHANGE",
                context=context,
                tradeoffs={
                    "accepted": "rebuild index projection after substantial structure change",
                    "rejected": "partial patch that may leave stale anchors",
                },
            )
        return PipelineDecision(
            decision_type="ingest_refresh",
            selected_action="partial_refresh",
            risk_level="low",
            reason_code="SMALL_CONTENT_CHANGE",
            context=context,
            tradeoffs={
                "accepted": "reuse stable chunks and only embed/index changed chunks",
                "rejected": "full reindex for a small source change",
            },
        )

    def opensearch_fallback(self, *, query: str, category: str | None, top_k: int, error: str) -> PipelineDecision:
        return PipelineDecision(
            decision_type="retrieval_backend",
            selected_action="pgvector_fallback",
            risk_level="medium",
            reason_code="OPENSEARCH_UNAVAILABLE",
            context={"query": query, "category": category, "top_k": top_k, "error": error},
            tradeoffs={
                "accepted": "serve degraded vector retrieval from PostgreSQL ledger",
                "rejected": "fail user-facing AI request when retrieval index is down",
            },
        )


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in normalized.split("\n"))
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def hash_text(value: str | bytes) -> str:
    if isinstance(value, bytes):
        payload = value
    else:
        payload = value.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def hash_json(value: dict[str, Any]) -> str:
    return hash_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def build_embedding_input_hash(
    *,
    content_hash: str,
    embedding_model: str,
    embedding_dim: int,
    normalization_version: str = NORMALIZATION_VERSION,
) -> str:
    return hash_json(
        {
            "content_hash": content_hash,
            "embedding_model": embedding_model,
            "embedding_dim": embedding_dim,
            "normalization_version": normalization_version,
        }
    )


def build_index_payload_hash(
    *,
    title: str,
    content_hash: str,
    category: str,
    tags: list[str],
    source_grade: str,
    status: str,
    embedding_input_hash: str,
    source_version: int,
) -> str:
    return hash_json(
        {
            "title": title,
            "content_hash": content_hash,
            "category": category,
            "tags": sorted(tags),
            "source_grade": source_grade,
            "status": status,
            "embedding_input_hash": embedding_input_hash,
            "source_version": source_version,
        }
    )


def split_over_max(text_value: str, max_size: int) -> list[str]:
    if len(text_value) <= max_size:
        return [text_value]

    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?。！？])\s+", text_value) if sentence.strip()]
    if len(sentences) <= 1:
        return [text_value[i : i + max_size] for i in range(0, len(text_value), max_size)]

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(sentence[i : i + max_size] for i in range(0, len(sentence), max_size))
            continue
        candidate = sentence if not current else f"{current} {sentence}"
        if len(candidate) <= max_size:
            current = candidate
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def estimate_token_count(value: str) -> int:
    return max(1, len(value) // 4)


def origin_type_for_path(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "file_markdown"
    if suffix == ".pdf":
        return "file_pdf"
    return "file_text"
