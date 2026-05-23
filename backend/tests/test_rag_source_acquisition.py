import pytest

from app.core.config import Settings
from app.services import rag_source_acquisition
from app.services.rag_source_acquisition import RAGSourceAcquisitionError, RAGUrlFetcher


class FakeResponse:
    def __init__(self, *, content: bytes, content_type: str, status_code: int = 200):
        self.status_code = status_code
        self.headers = {"content-type": content_type}
        self.content = content
        self.text = content.decode("utf-8", errors="ignore")
        self.url = "https://example.org/source"


class FakeAsyncClient:
    response: FakeResponse

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url):
        return self.response


@pytest.mark.asyncio
async def test_url_fetcher_accepts_pdf_binary(monkeypatch):
    FakeAsyncClient.response = FakeResponse(content=b"%PDF-1.4\nbody", content_type="application/pdf")
    monkeypatch.setattr(rag_source_acquisition.httpx, "AsyncClient", FakeAsyncClient)

    fetched = await RAGUrlFetcher(Settings()).fetch_pdf("https://example.org/source.pdf")

    assert fetched.content_type == "application/pdf"
    assert fetched.text == ""
    assert fetched.metadata()["content_length"] == len(b"%PDF-1.4\nbody")


@pytest.mark.asyncio
async def test_url_fetcher_rejects_non_pdf_for_pdf_fetch(monkeypatch):
    FakeAsyncClient.response = FakeResponse(content=b"<html></html>", content_type="text/html")
    monkeypatch.setattr(rag_source_acquisition.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(RAGSourceAcquisitionError, match="Unsupported URL content type"):
        await RAGUrlFetcher(Settings()).fetch_pdf("https://example.org/source.pdf")


@pytest.mark.asyncio
async def test_url_fetcher_rejects_oversized_pdf(monkeypatch):
    FakeAsyncClient.response = FakeResponse(content=b"%PDF-1.4\nbody", content_type="application/pdf")
    monkeypatch.setattr(rag_source_acquisition.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(RAGSourceAcquisitionError, match="exceeds RAG_URL_MAX_BYTES"):
        await RAGUrlFetcher(Settings(RAG_URL_MAX_BYTES=5)).fetch_pdf("https://example.org/source.pdf")
