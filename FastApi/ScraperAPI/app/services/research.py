from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.research_repository import ResearchRepository
from app.schemas import ResearchRequest, ResearchResponse, ScrapeRequest, SourceResult
from app.services.organizer import OrganizerService
from app.services.scraper import ScraperService


class ResearchService:
    async def run(self, payload: ResearchRequest) -> ResearchResponse:
        created_at = datetime.now(timezone.utc)
        research_id = str(uuid4())
        urls = [str(url) for url in payload.urls[: payload.max_sources]]

        sources: list[SourceResult] = []
        scraper = ScraperService()
        organizer = OrganizerService()

        if not urls:
            sources.append(
                SourceResult(
                    url="source-discovery",
                    error=(
                        "Descoberta automatica de fontes ainda nao configurada. "
                        "Envie URLs no campo 'urls' para esta versao."
                    ),
                )
            )

        for url in urls:
            try:
                scrape_response = await scraper.scrape(ScrapeRequest(url=url))
                text = scrape_response.extraction.text
                summary, key_points = organizer.summarize_source(text)
                sources.append(
                    SourceResult(
                        url=scrape_response.final_url or scrape_response.url,
                        status_code=scrape_response.status_code,
                        title=scrape_response.extraction.title,
                        summary=summary,
                        key_points=key_points,
                        fetched_at=scrape_response.fetched_at,
                    )
                )
            except Exception as exc:
                sources.append(SourceResult(url=url, error=str(exc)))

        metadata = {
            "source_count": len(sources),
            "output_format": payload.output_format,
            "organizer": "local",
        }

        summary, topics, entities, markdown_report = organizer.organize(
            query=payload.query,
            language=payload.language,
            focus=payload.focus,
            sources=sources,
        )

        successful_sources = [source for source in sources if not source.error]
        status = "completed" if successful_sources else "failed"
        if successful_sources and len(successful_sources) < len(sources):
            status = "partial"
        metadata["successful_source_count"] = len(successful_sources)

        response = ResearchResponse(
            id=research_id,
            query=payload.query,
            language=payload.language,
            status=status,
            summary=summary,
            topics=topics,
            entities=entities,
            sources=sources,
            markdown_report=markdown_report,
            created_at=created_at,
            metadata=metadata,
        )

        repository = ResearchRepository()
        repository.save(response, payload)
        return response
