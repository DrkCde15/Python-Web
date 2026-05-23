from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
import httpx

from app.config import get_settings
from app.schemas import ScrapeRequest, ScrapeResponse
from app.security import validate_public_url
from app.services.extractor import ExtractorService


class ScraperService:
    async def scrape(self, payload: ScrapeRequest) -> ScrapeResponse:
        settings = get_settings()
        raw_url = str(payload.url)
        validate_public_url(raw_url)

        headers = {
            "User-Agent": payload.user_agent or settings.default_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        timeout = payload.timeout_seconds or settings.request_timeout_seconds

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                response = await client.get(raw_url, headers=headers)
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="Timeout ao coletar a URL.") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Erro ao coletar URL: {exc}") from exc

        content_type = response.headers.get("content-type")
        if content_type and "html" not in content_type.lower():
            raise HTTPException(
                status_code=415,
                detail=f"Conteudo nao HTML recebido: {content_type}",
            )

        html_bytes = response.content[: settings.max_html_bytes + 1]
        if len(html_bytes) > settings.max_html_bytes:
            raise HTTPException(status_code=413, detail="Pagina excede o tamanho maximo configurado.")

        html = response.text
        extractor = ExtractorService()
        extracted = extractor.extract(
            html=html,
            url=str(response.url),
            include_text=payload.include_text,
            include_links=payload.include_links,
        )

        return ScrapeResponse(
            url=raw_url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=content_type,
            fetched_at=datetime.now(timezone.utc),
            extraction=extracted.extraction,
        )
