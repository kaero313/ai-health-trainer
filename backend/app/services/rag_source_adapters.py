from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.rag_pipeline import ParsedDocument


ACQUISITION_URL_HTML = "url_html"
ACQUISITION_LOCAL_FILE = "local_file"


@dataclass(frozen=True)
class CatalogSource:
    key: str | None
    acquisition_type: str
    url: str | None
    path: str | None
    parser_type: str
    title: str | None
    category: str
    tags: list[str]
    source_type: str
    source_grade: str
    license_value: str | None
    language: str
    author_or_org: str | None
    refresh_policy: str
    refresh_interval_hours: int | None
    curation_method: str | None
    reference_urls: list[str]


@dataclass(frozen=True)
class AcquiredSource:
    catalog_source: CatalogSource
    parsed: ParsedDocument
    source_url: str | None
    origin_type: str
    origin_uri: str
    acquisition_metadata: dict[str, Any]


class UrlHtmlSourceAdapter:
    def __init__(self, rag_service: Any):
        self.rag_service = rag_service

    async def acquire(self, catalog_source: CatalogSource, *, catalog_file: Path) -> AcquiredSource:
        if not catalog_source.url:
            raise ValueError("url_html catalog source requires url")
        fetched = await self.rag_service.url_fetcher.fetch(catalog_source.url)
        parsed = self.rag_service._parse_fetched_url(
            fetched,
            title=catalog_source.title,
            extra_metadata=_catalog_metadata(catalog_source, catalog_file),
        )
        return AcquiredSource(
            catalog_source=catalog_source,
            parsed=parsed,
            source_url=fetched.final_url,
            origin_type="url_html",
            origin_uri=catalog_source.url,
            acquisition_metadata=parsed.fetch_metadata or {},
        )


def _catalog_metadata(catalog_source: CatalogSource, catalog_file: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "catalog_key": catalog_source.key,
        "catalog_file": str(catalog_file),
        "acquisition_type": catalog_source.acquisition_type,
        "curation_method": catalog_source.curation_method,
        "reference_urls": catalog_source.reference_urls,
    }
    return {key: value for key, value in metadata.items() if value is not None and value != ""}


def load_catalog_sources(payload: Any) -> list[CatalogSource]:
    raw_sources = payload.get("sources", []) if isinstance(payload, dict) else payload
    if not isinstance(raw_sources, list):
        raise ValueError("Catalog file must contain a sources list")
    return [_load_catalog_source(source) for source in raw_sources]


def _load_catalog_source(source: dict[str, Any]) -> CatalogSource:
    acquisition_type = str(source.get("acquisition_type") or (ACQUISITION_URL_HTML if source.get("url") else ACQUISITION_LOCAL_FILE))
    parser_type = str(source.get("parser_type") or ("html" if acquisition_type == ACQUISITION_URL_HTML else "auto"))
    return CatalogSource(
        key=source.get("key"),
        acquisition_type=acquisition_type,
        url=source.get("url"),
        path=source.get("path"),
        parser_type=parser_type,
        title=source.get("title"),
        category=source["category"],
        tags=list(source.get("tags") or []),
        source_type=source.get("source_type", "official_guideline" if acquisition_type == ACQUISITION_URL_HTML else "curated_internal_summary"),
        source_grade=source.get("source_grade", "A" if acquisition_type == ACQUISITION_URL_HTML else "B"),
        license_value=source.get("license"),
        language=source.get("language", "en" if acquisition_type == ACQUISITION_URL_HTML else "ko"),
        author_or_org=source.get("author_or_org"),
        refresh_policy=source.get("refresh_policy", "scheduled" if acquisition_type == ACQUISITION_URL_HTML else "manual"),
        refresh_interval_hours=_optional_int(source.get("refresh_interval_hours")),
        curation_method=source.get("curation_method"),
        reference_urls=list(source.get("reference_urls") or ([] if not source.get("url") else [source["url"]])),
    )


def _optional_int(value: object) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)
