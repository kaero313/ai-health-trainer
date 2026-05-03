from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.core.config import Settings
from app.services.rag_pipeline import hash_text


class RAGSourceAcquisitionError(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchedUrlContent:
    requested_url: str
    final_url: str
    content_type: str | None
    etag: str | None
    last_modified: str | None
    fetched_at: datetime
    raw_content: bytes
    text: str

    @property
    def raw_content_hash(self) -> str:
        return hash_text(self.raw_content)

    def metadata(self) -> dict[str, object]:
        return {
            "requested_url": self.requested_url,
            "final_url": self.final_url,
            "content_type": self.content_type,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "fetched_at": self.fetched_at.isoformat(),
            "raw_content_hash": self.raw_content_hash,
        }


class RAGUrlFetcher:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def fetch(self, url: str) -> FetchedUrlContent:
        timeout = httpx.Timeout(self.settings.RAG_URL_FETCH_TIMEOUT_SECONDS)
        headers = {"User-Agent": self.settings.RAG_URL_USER_AGENT}
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
            response = await client.get(url)

        if response.status_code < 200 or response.status_code >= 300:
            raise RAGSourceAcquisitionError(f"URL fetch failed with status {response.status_code}: {url}")

        content_type = response.headers.get("content-type")
        if content_type and "html" not in content_type.lower() and "text" not in content_type.lower():
            raise RAGSourceAcquisitionError(f"Unsupported URL content type: {content_type}")

        raw_content = response.content
        if len(raw_content) > self.settings.RAG_URL_MAX_BYTES:
            raise RAGSourceAcquisitionError(
                f"URL content exceeds RAG_URL_MAX_BYTES ({len(raw_content)} > {self.settings.RAG_URL_MAX_BYTES})"
            )

        return FetchedUrlContent(
            requested_url=url,
            final_url=str(response.url),
            content_type=content_type,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            fetched_at=datetime.now(timezone.utc),
            raw_content=raw_content,
            text=response.text,
        )
