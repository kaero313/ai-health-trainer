from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from uuid import uuid4

from google import genai
from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.rag import RagChunk, RagIngestJob, RagRetrievalTrace, RagSource
from app.services.rag_index_service import RAGIndexError, RAGIndexService


class RAGService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.index_service = RAGIndexService(settings)

    async def get_embedding(self, text_value: str) -> list[float]:
        normalized = text_value.strip()
        if not normalized:
            raise ValueError("Text for embedding must not be empty")

        embedding_model = self._embedding_model_name()
        result = await self.client.aio.models.embed_content(
            model=embedding_model,
            contents=normalized,
        )
        embeddings = result.embeddings or []
        if not embeddings or embeddings[0].values is None:
            raise ValueError("Embedding response did not include values")
        return [float(value) for value in embeddings[0].values]

    async def search(
        self,
        query: str,
        category: str | None = None,
        top_k: int = 3,
        *,
        user_id: int | None = None,
        request_type: str = "unknown",
        request_id: int | None = None,
        trace_group_id: str | None = None,
    ) -> list[dict]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        safe_top_k = max(1, top_k)
        group_id = trace_group_id or str(uuid4())
        query_embedding = await self.get_embedding(normalized_query)

        try:
            documents = await self._search_opensearch(normalized_query, query_embedding, category, safe_top_k)
            search_backend = "opensearch"
            search_mode = "hybrid"
        except RAGIndexError:
            documents = await self._search_pgvector(normalized_query, query_embedding, category, safe_top_k)
            search_backend = "pgvector_fallback"
            search_mode = "vector"

        for document in documents:
            document["rag_trace_group_id"] = group_id
            document["search_backend"] = search_backend
            document["search_mode"] = search_mode

        if user_id is not None:
            await self._save_retrieval_traces(
                documents=documents,
                user_id=user_id,
                request_type=request_type,
                request_id=request_id,
                trace_group_id=group_id,
                query_text=normalized_query,
                category=category,
                top_k=safe_top_k,
                search_backend=search_backend,
                search_mode=search_mode,
            )

        return documents

    async def ingest_document(
        self,
        title: str,
        content: str,
        category: str,
        source: str = "",
        *,
        tags: list[str] | None = None,
        source_type: str = "internal_policy",
        source_grade: str = "B",
        license_value: str | None = "internal-summary",
        language: str = "ko",
        author_or_org: str | None = None,
    ) -> int:
        normalized_content = content.strip()
        chunks = self._chunk_text(normalized_content)
        content_hash = self._hash_text(normalized_content)
        started_at = datetime.now(timezone.utc)
        embedding_model = self._embedding_model_name()

        job = RagIngestJob(
            job_type="create",
            status="running",
            requested_by="cli",
            input_hash=content_hash,
            embedding_model=embedding_model,
            target_index=self.settings.RAG_OPENSEARCH_INDEX,
            chunks_total=len(chunks),
            started_at=started_at,
        )
        self.db.add(job)

        if not chunks:
            job.status = "succeeded"
            job.finished_at = datetime.now(timezone.utc)
            await self.db.commit()
            return 0

        source_record = RagSource(
            title=title,
            source_type=source_type,
            source_url=source or None,
            source_grade=source_grade,
            license=license_value,
            category=category,
            tags=self._normalize_tags(tags),
            language=language,
            author_or_org=author_or_org,
            reviewed_at=datetime.now(timezone.utc),
            status="active",
            version=1,
            content_hash=content_hash,
        )
        self.db.add(source_record)
        await self.db.flush()
        job.source_id = source_record.id

        chunk_records: list[RagChunk] = []
        try:
            total = len(chunks)
            for idx, chunk in enumerate(chunks, start=1):
                embedding = await self.get_embedding(chunk)
                chunk_record = RagChunk(
                    source_id=source_record.id,
                    chunk_index=idx,
                    title=f"{title} ({idx}/{total})",
                    content=chunk,
                    content_hash=self._hash_text(chunk),
                    category=category,
                    tags=self._normalize_tags(tags),
                    embedding=embedding,
                    embedding_model=embedding_model,
                    embedding_dim=len(embedding),
                    opensearch_index=self.settings.RAG_OPENSEARCH_INDEX,
                    index_status="pending",
                    token_count=self._estimate_token_count(chunk),
                    status="active",
                    version=1,
                )
                self.db.add(chunk_record)
                chunk_records.append(chunk_record)

            await self.db.flush()
            for chunk_record in chunk_records:
                chunk_record.opensearch_document_id = str(chunk_record.id)

            indexed_succeeded = 0
            for chunk_record in chunk_records:
                try:
                    await self.index_service.index_chunk(chunk_record, source_record)
                except RAGIndexError:
                    chunk_record.index_status = "failed"
                    continue
                chunk_record.index_status = "indexed"
                chunk_record.indexed_at = datetime.now(timezone.utc)
                indexed_succeeded += 1

            job.chunks_succeeded = len(chunk_records)
            job.indexed_total = len(chunk_records)
            job.indexed_succeeded = indexed_succeeded
            job.indexed_failed = len(chunk_records) - indexed_succeeded
            job.status = "succeeded" if job.indexed_failed == 0 else "failed"
            if job.indexed_failed:
                job.error_code = "OPENSEARCH_INDEX_FAILED"
                job.error_message = "일부 chunk의 OpenSearch 색인에 실패했습니다"
            job.finished_at = datetime.now(timezone.utc)
            await self.db.commit()
        except Exception:
            job.status = "failed"
            job.chunks_failed = len(chunks)
            job.error_code = "INGEST_FAILED"
            job.error_message = "RAG 문서 ingest에 실패했습니다"
            job.finished_at = datetime.now(timezone.utc)
            await self.db.rollback()
            raise

        return len(chunk_records)

    async def ensure_index(self) -> bool:
        return await self.index_service.ensure_index()

    async def delete_index(self) -> bool:
        return await self.index_service.delete_index()

    async def reindex(self, source_id: int | None = None) -> dict[str, int]:
        await self.ensure_index()
        stmt = (
            select(RagChunk, RagSource)
            .join(RagSource, RagSource.id == RagChunk.source_id)
            .where(RagChunk.status == "active", RagSource.status == "active")
            .order_by(RagChunk.id.asc())
        )
        if source_id is not None:
            stmt = stmt.where(RagChunk.source_id == source_id)

        rows = (await self.db.execute(stmt)).all()
        indexed = 0
        failed = 0
        for chunk, source in rows:
            try:
                await self.index_service.index_chunk(chunk, source)
            except RAGIndexError:
                chunk.index_status = "failed"
                failed += 1
                continue
            chunk.index_status = "indexed"
            chunk.indexed_at = datetime.now(timezone.utc)
            chunk.opensearch_index = self.settings.RAG_OPENSEARCH_INDEX
            chunk.opensearch_document_id = str(chunk.id)
            indexed += 1
        await self.db.commit()
        return {"indexed": indexed, "failed": failed}

    async def archive_source(self, source_id: int) -> dict[str, int]:
        source = await self.db.get(RagSource, source_id)
        if source is None:
            return {"sources": 0, "chunks": 0}

        source.status = "archived"
        chunks = (
            await self.db.execute(select(RagChunk).where(RagChunk.source_id == source_id))
        ).scalars().all()

        archived_chunks = 0
        for chunk in chunks:
            chunk.status = "archived"
            chunk.index_status = "deleted"
            archived_chunks += 1
            try:
                await self.index_service.delete_chunk(chunk.id)
            except RAGIndexError:
                pass
        await self.db.commit()
        return {"sources": 1, "chunks": archived_chunks}

    async def mark_traces_request_id(self, trace_group_id: str | None, request_id: int | None) -> None:
        if not trace_group_id or request_id is None:
            return
        await self.db.execute(
            update(RagRetrievalTrace)
            .where(RagRetrievalTrace.rag_trace_group_id == trace_group_id)
            .values(request_id=request_id)
        )

    async def _search_opensearch(
        self,
        query: str,
        query_embedding: list[float],
        category: str | None,
        top_k: int,
    ) -> list[dict]:
        search_size = max(top_k * 3, top_k)
        keyword_hits = await self.index_service.keyword_search(query, category, search_size)
        vector_hits = await self.index_service.vector_search(query_embedding, category, search_size)
        merged_hits = self._merge_hybrid_hits(keyword_hits, vector_hits)[:top_k]
        chunk_ids = [int(hit["chunk_id"]) for hit in merged_hits if str(hit.get("chunk_id", "")).isdigit()]
        if not chunk_ids:
            return []

        chunk_rows = await self._load_active_chunks(chunk_ids)
        documents: list[dict] = []
        for rank, hit in enumerate(merged_hits, start=1):
            chunk_id = int(hit["chunk_id"])
            row = chunk_rows.get(chunk_id)
            if row is None:
                continue
            chunk, source = row
            documents.append(
                self._build_document(
                    chunk,
                    source,
                    rank=rank,
                    score=hit.get("score"),
                    similarity=hit.get("vector_score"),
                    keyword_score=hit.get("keyword_score"),
                    vector_score=hit.get("vector_score"),
                    index_name=self.settings.RAG_OPENSEARCH_ALIAS,
                    index_version=self.settings.RAG_OPENSEARCH_INDEX,
                )
            )
        return documents

    async def _search_pgvector(
        self,
        query: str,
        query_embedding: list[float],
        category: str | None,
        top_k: int,
    ) -> list[dict]:
        _ = query
        vec_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        category_filter = ""
        params: dict[str, object] = {"query_vec": vec_str, "top_k": top_k}
        if category is not None:
            category_filter = "AND c.category = :category"
            params["category"] = category

        stmt = text(
            """
            SELECT c.id, c.source_id, c.title, c.content, c.category,
                   c.tags,
                   s.title AS source_title,
                   s.source_grade,
                   1 - (c.embedding <=> (:query_vec)::vector) AS similarity
            FROM rag_chunks c
            JOIN rag_sources s ON s.id = c.source_id
            WHERE c.status = 'active'
              AND s.status = 'active'
              {category_filter}
            ORDER BY c.embedding <=> (:query_vec)::vector
            LIMIT :top_k
            """.format(category_filter=category_filter)
        )
        rows = (await self.db.execute(stmt, params)).mappings().all()
        return [
            {
                "chunk_id": int(row["id"]),
                "source_id": int(row["source_id"]),
                "title": str(row["title"]),
                "source_title": str(row["source_title"]),
                "content": str(row["content"]),
                "category": str(row["category"]),
                "tags": list(row["tags"] or []),
                "source_grade": str(row["source_grade"]),
                "rank": idx,
                "score": float(row["similarity"]),
                "similarity": float(row["similarity"]),
                "keyword_score": None,
                "vector_score": float(row["similarity"]),
                "index_name": None,
                "index_version": None,
            }
            for idx, row in enumerate(rows, start=1)
        ]

    async def _load_active_chunks(self, chunk_ids: list[int]) -> dict[int, tuple[RagChunk, RagSource]]:
        stmt = (
            select(RagChunk, RagSource)
            .join(RagSource, RagSource.id == RagChunk.source_id)
            .where(
                and_(
                    RagChunk.id.in_(chunk_ids),
                    RagChunk.status == "active",
                    RagSource.status == "active",
                )
            )
        )
        rows = (await self.db.execute(stmt)).all()
        return {chunk.id: (chunk, source) for chunk, source in rows}

    async def _save_retrieval_traces(
        self,
        *,
        documents: list[dict],
        user_id: int,
        request_type: str,
        request_id: int | None,
        trace_group_id: str,
        query_text: str,
        category: str | None,
        top_k: int,
        search_backend: str,
        search_mode: str,
    ) -> None:
        for idx, document in enumerate(documents, start=1):
            self.db.add(
                RagRetrievalTrace(
                    user_id=user_id,
                    request_type=request_type,
                    request_id=request_id,
                    rag_trace_group_id=trace_group_id,
                    query_text=query_text,
                    category_filter=category,
                    search_backend=search_backend,
                    search_mode=search_mode,
                    index_name=document.get("index_name"),
                    index_version=document.get("index_version"),
                    top_k=top_k,
                    chunk_id=document.get("chunk_id"),
                    source_id=document.get("source_id"),
                    rank=int(document.get("rank") or idx),
                    score=document.get("score"),
                    similarity=document.get("similarity"),
                    keyword_score=document.get("keyword_score"),
                    vector_score=document.get("vector_score"),
                    used_in_prompt=True,
                    embedding_model=self._embedding_model_name(),
                )
            )
        await self.db.commit()

    def _merge_hybrid_hits(self, keyword_hits: list[dict], vector_hits: list[dict]) -> list[dict]:
        merged: dict[str, dict] = {}

        for rank, hit in enumerate(keyword_hits, start=1):
            source = hit.get("_source") or {}
            chunk_id = str(source.get("chunk_id") or hit.get("_id") or "")
            if not chunk_id:
                continue
            record = merged.setdefault(chunk_id, {"chunk_id": chunk_id, "score": 0.0})
            raw_score = float(hit.get("_score") or 0.0)
            record["keyword_score"] = raw_score
            record["score"] += self.settings.RAG_KEYWORD_WEIGHT / rank

        for rank, hit in enumerate(vector_hits, start=1):
            source = hit.get("_source") or {}
            chunk_id = str(source.get("chunk_id") or hit.get("_id") or "")
            if not chunk_id:
                continue
            record = merged.setdefault(chunk_id, {"chunk_id": chunk_id, "score": 0.0})
            raw_score = float(hit.get("_score") or 0.0)
            record["vector_score"] = raw_score
            record["score"] += self.settings.RAG_VECTOR_WEIGHT / rank

        return sorted(merged.values(), key=lambda item: float(item.get("score") or 0.0), reverse=True)

    def _build_document(
        self,
        chunk: RagChunk,
        source: RagSource,
        *,
        rank: int,
        score: float | None,
        similarity: float | None,
        keyword_score: float | None,
        vector_score: float | None,
        index_name: str | None,
        index_version: str | None,
    ) -> dict:
        return {
            "chunk_id": chunk.id,
            "source_id": source.id,
            "title": chunk.title,
            "source_title": source.title,
            "content": chunk.content,
            "category": chunk.category,
            "tags": list(chunk.tags or []),
            "source_grade": source.source_grade,
            "rank": rank,
            "score": score,
            "similarity": similarity,
            "keyword_score": keyword_score,
            "vector_score": vector_score,
            "index_name": index_name,
            "index_version": index_version,
        }

    def _chunk_text(self, text_value: str, min_size: int = 50, max_size: int = 1000) -> list[str]:
        normalized = text_value.replace("\r\n", "\n").strip()
        if not normalized:
            return []

        paragraphs = [paragraph.strip() for paragraph in normalized.split("\n\n") if paragraph.strip()]
        raw_chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            paragraph_chunks = self._split_over_max(paragraph, max_size)
            for paragraph_chunk in paragraph_chunks:
                if not current:
                    current = paragraph_chunk
                    continue

                candidate = f"{current}\n\n{paragraph_chunk}"
                if len(candidate) <= max_size:
                    current = candidate
                else:
                    raw_chunks.append(current)
                    current = paragraph_chunk

        if current:
            raw_chunks.append(current)

        merged_chunks: list[str] = []
        for chunk in raw_chunks:
            if len(chunk) >= min_size:
                merged_chunks.append(chunk)
                continue

            if merged_chunks and len(f"{merged_chunks[-1]}\n\n{chunk}") <= max_size:
                merged_chunks[-1] = f"{merged_chunks[-1]}\n\n{chunk}"
                continue

            merged_chunks.append(chunk)

        return [chunk.strip() for chunk in merged_chunks if chunk.strip()]

    def _embedding_model_name(self) -> str:
        return self.settings.AI_EMBEDDING_MODEL.removeprefix("models/")

    @staticmethod
    def _split_over_max(text_value: str, max_size: int) -> list[str]:
        if len(text_value) <= max_size:
            return [text_value]

        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text_value) if sentence.strip()]
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

            if not current:
                current = sentence
                continue

            candidate = f"{current} {sentence}"
            if len(candidate) <= max_size:
                current = candidate
            else:
                chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return chunks

    @staticmethod
    def _hash_text(value: str) -> str:
        return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_tags(tags: list[str] | None) -> list[str]:
        if not tags:
            return []
        return [tag.strip() for tag in tags if tag.strip()]

    @staticmethod
    def _estimate_token_count(value: str) -> int:
        return max(1, len(value) // 4)
