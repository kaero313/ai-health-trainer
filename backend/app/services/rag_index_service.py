from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings
from app.models.rag import RagChunk, RagSource

try:
    from opensearchpy import AsyncOpenSearch
except ModuleNotFoundError:  # pragma: no cover - exercised only when dependency is missing
    AsyncOpenSearch = None  # type: ignore[assignment]


KNN_METHOD = {
    "name": "hnsw",
    "engine": "lucene",
    "space_type": "cosinesimil",
    "parameters": {
        "m": 16,
        "ef_construction": 100,
    },
}


class RAGIndexError(Exception):
    pass


class RAGIndexService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.index_name = settings.RAG_OPENSEARCH_INDEX
        self.alias_name = settings.RAG_OPENSEARCH_ALIAS

    def _client(self):
        if AsyncOpenSearch is None:
            raise RAGIndexError("opensearch-py is not installed")
        return AsyncOpenSearch(
            hosts=[self.settings.OPENSEARCH_URL],
            use_ssl=self.settings.OPENSEARCH_URL.startswith("https://"),
            verify_certs=False,
        )

    def build_index_body(self) -> dict[str, Any]:
        return {
            "settings": {
                "index": {
                    "knn": True,
                }
            },
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "source_id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "content": {"type": "text"},
                    "category": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "source_grade": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "language": {"type": "keyword"},
                    "source_url": {"type": "keyword"},
                    "source_title": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "content_hash": {"type": "keyword"},
                    "anchor_hash": {"type": "keyword"},
                    "embedding_input_hash": {"type": "keyword"},
                    "index_payload_hash": {"type": "keyword"},
                    "source_version": {"type": "integer"},
                    "chunk_version": {"type": "integer"},
                    "chunk_strategy": {"type": "keyword"},
                    "chunk_anchor": {"type": "keyword"},
                    "page_number": {"type": "integer"},
                    "embedding_model": {"type": "keyword"},
                    "embedding_dim": {"type": "integer"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 3072,
                        "method": KNN_METHOD,
                    },
                    "indexed_at": {"type": "date"},
                }
            },
        }

    async def ensure_index(self) -> bool:
        client = self._client()
        try:
            exists = await client.indices.exists(index=self.index_name)
            if not exists:
                await client.indices.create(index=self.index_name, body=self.build_index_body())

            alias_exists = await client.indices.exists_alias(name=self.alias_name)
            if not alias_exists:
                await client.indices.put_alias(index=self.index_name, name=self.alias_name)
            return True
        except Exception as exc:
            raise RAGIndexError(str(exc)) from exc
        finally:
            await client.close()

    async def delete_index(self) -> bool:
        client = self._client()
        try:
            exists = await client.indices.exists(index=self.index_name)
            if exists:
                await client.indices.delete(index=self.index_name)
            return True
        except Exception as exc:
            raise RAGIndexError(str(exc)) from exc
        finally:
            await client.close()

    async def index_status(self) -> dict[str, Any]:
        client = self._client()
        try:
            exists = await client.indices.exists(index=self.index_name)
            alias_exists = await client.indices.exists_alias(name=self.alias_name)
            if not exists:
                return {
                    "index": self.index_name,
                    "alias": self.alias_name,
                    "exists": False,
                    "alias_exists": bool(alias_exists),
                }

            rows = await client.cat.indices(index=self.index_name, format="json")
            row = rows[0] if rows else {}
            return {
                "index": self.index_name,
                "alias": self.alias_name,
                "exists": True,
                "alias_exists": bool(alias_exists),
                "health": row.get("health"),
                "status": row.get("status"),
                "docs_count": _safe_int(row.get("docs.count")),
                "docs_deleted": _safe_int(row.get("docs.deleted")),
                "store_size": row.get("store.size"),
                "primary_store_size": row.get("pri.store.size"),
            }
        except Exception as exc:
            raise RAGIndexError(str(exc)) from exc
        finally:
            await client.close()

    def build_document(self, chunk: RagChunk, source: RagSource) -> dict[str, Any]:
        return {
            "chunk_id": str(chunk.id),
            "source_id": str(source.id),
            "title": chunk.title,
            "content": chunk.content,
            "category": chunk.category,
            "tags": list(chunk.tags or []),
            "source_grade": source.source_grade,
            "status": chunk.status if source.status == "active" else source.status,
            "language": source.language,
            "source_url": source.source_url,
            "source_title": source.title,
            "content_hash": chunk.content_hash,
            "anchor_hash": chunk.anchor_hash,
            "embedding_input_hash": chunk.embedding_input_hash,
            "index_payload_hash": chunk.index_payload_hash,
            "source_version": chunk.source_version,
            "chunk_version": chunk.version,
            "chunk_strategy": chunk.chunk_strategy,
            "chunk_anchor": chunk.chunk_anchor,
            "page_number": chunk.page_number,
            "embedding_model": chunk.embedding_model,
            "embedding_dim": chunk.embedding_dim,
            "embedding": list(chunk.embedding),
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def index_chunk(self, chunk: RagChunk, source: RagSource) -> None:
        await self.ensure_index()
        client = self._client()
        try:
            await client.index(
                index=self.index_name,
                id=str(chunk.id),
                body=self.build_document(chunk, source),
                refresh=True,
            )
        except Exception as exc:
            raise RAGIndexError(str(exc)) from exc
        finally:
            await client.close()

    async def delete_chunk(self, chunk_id: int) -> None:
        client = self._client()
        try:
            await client.delete(index=self.index_name, id=str(chunk_id), ignore=[404], refresh=True)
        except Exception as exc:
            raise RAGIndexError(str(exc)) from exc
        finally:
            await client.close()

    async def keyword_search(self, query: str, category: str | None, size: int) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = [{"term": {"status": "active"}}]
        if category:
            filters.append({"term": {"category": category}})

        body = {
            "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^2", "content", "source_title"],
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
        }
        return await self._search(body)

    async def vector_search(self, query_embedding: list[float], category: str | None, size: int) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = [{"term": {"status": "active"}}]
        if category:
            filters.append({"term": {"category": category}})

        body = {
            "size": size,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": size,
                        "filter": {"bool": {"filter": filters}},
                    }
                }
            },
        }
        return await self._search(body)

    async def _search(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        client = self._client()
        try:
            response = await client.search(index=self.alias_name, body=body)
        except Exception as exc:
            raise RAGIndexError(str(exc)) from exc
        finally:
            await client.close()

        hits = response.get("hits", {}).get("hits", [])
        return [hit for hit in hits if isinstance(hit, dict)]


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
