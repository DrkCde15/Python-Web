from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class LinkItem(BaseModel):
    text: str = ""
    url: str


class PageMetadata(BaseModel):
    title: str | None = None
    description: str | None = None
    language: str | None = None
    canonical_url: str | None = None
    author: str | None = None
    published_time: str | None = None


class ExtractedContent(BaseModel):
    url: str | None = None
    title: str | None = None
    text: str | None = None
    word_count: int = 0
    links: list[LinkItem] = Field(default_factory=list)
    metadata: PageMetadata = Field(default_factory=PageMetadata)


class ScrapeRequest(BaseModel):
    url: HttpUrl
    include_text: bool = True
    include_links: bool = True
    user_agent: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0, le=60)


class ScrapeResponse(BaseModel):
    url: str
    final_url: str | None = None
    status_code: int
    content_type: str | None = None
    fetched_at: datetime
    extraction: ExtractedContent


class ExtractRequest(BaseModel):
    html: str = Field(min_length=1)
    url: HttpUrl | None = None
    include_text: bool = True
    include_links: bool = True


class ExtractResponse(BaseModel):
    extraction: ExtractedContent


class SourceResult(BaseModel):
    url: str
    status_code: int | None = None
    title: str | None = None
    summary: str | None = None
    key_points: list[str] = Field(default_factory=list)
    error: str | None = None
    fetched_at: datetime | None = None


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    urls: list[HttpUrl] = Field(default_factory=list)
    language: str = "pt-BR"
    max_sources: int = Field(default=5, ge=1, le=20)
    focus: list[str] = Field(default_factory=list)
    output_format: Literal["json", "report"] = "report"

    @field_validator("focus")
    @classmethod
    def limit_focus_items(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()][:10]


class ResearchInsight(BaseModel):
    name: str
    notes: list[str] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    id: str
    query: str
    language: str
    status: Literal["completed", "partial", "failed"]
    summary: str
    topics: list[ResearchInsight] = Field(default_factory=list)
    entities: dict[str, list[str]] = Field(default_factory=dict)
    sources: list[SourceResult] = Field(default_factory=list)
    markdown_report: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
