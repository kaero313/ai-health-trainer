import re

from google import genai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.rag_document import RagDocument


class RAGService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def get_embedding(self, text_value: str) -> list[float]:
        normalized = text_value.strip()
        if not normalized:
            raise ValueError("Text for embedding must not be empty")

        embedding_model = self.settings.AI_EMBEDDING_MODEL.removeprefix("models/")

        result = await self.client.aio.models.embed_content(
            model=embedding_model,
            contents=normalized,
        )
        embeddings = result.embeddings or []
        if not embeddings or embeddings[0].values is None:
            raise ValueError("Embedding response did not include values")
        return [float(value) for value in embeddings[0].values]

    async def search(self, query: str, category: str | None = None, top_k: int = 3) -> list[dict]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        safe_top_k = max(1, top_k)
        query_embedding = await self.get_embedding(normalized_query)
        vec_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        category_filter = ""
        params = {
            "query_vec": vec_str,
            "top_k": safe_top_k,
        }
        if category is not None:
            category_filter = "WHERE category = :category"
            params["category"] = category

        stmt = text(
            """
            SELECT id, title, content,
                   1 - (embedding <=> (:query_vec)::vector) as similarity
            FROM rag_documents
            {category_filter}
            ORDER BY embedding <=> (:query_vec)::vector
            LIMIT :top_k
            """.format(category_filter=category_filter)
        )
        result = await self.db.execute(stmt, params)
        rows = result.mappings().all()

        return [
            {
                "title": str(row["title"]),
                "content": str(row["content"]),
                "similarity": float(row["similarity"]),
            }
            for row in rows
        ]

    async def ingest_document(self, title: str, content: str, category: str, source: str = "") -> int:
        chunks = self._chunk_text(content)
        if not chunks:
            return 0

        total = len(chunks)
        documents: list[RagDocument] = []
        for idx, chunk in enumerate(chunks, start=1):
            embedding = await self.get_embedding(chunk)
            documents.append(
                RagDocument(
                    title=f"{title} ({idx}/{total})",
                    source=source or None,
                    category=category,
                    content=chunk,
                    embedding=embedding,
                )
            )

        try:
            self.db.add_all(documents)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return total

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

            if not merged_chunks:
                merged_chunks.append(chunk)
                continue

            merged_chunks.append(chunk)

        final_chunks: list[str] = []
        idx = 0
        while idx < len(merged_chunks):
            chunk = merged_chunks[idx]
            if len(chunk) >= min_size or idx + 1 >= len(merged_chunks):
                final_chunks.append(chunk)
                idx += 1
                continue

            next_chunk = merged_chunks[idx + 1]
            combined = f"{chunk}\n\n{next_chunk}"
            if len(combined) <= max_size:
                final_chunks.append(combined)
                idx += 2
                continue

            final_chunks.append(chunk)
            idx += 1

        return [chunk.strip() for chunk in final_chunks if chunk.strip()]

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
