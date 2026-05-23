from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.schemas import ScrapeRequest, ScrapeResponse
from app.services.scraper import ScraperService


router = APIRouter(prefix="/scrape", tags=["scrape"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=ScrapeResponse)
async def scrape_url(payload: ScrapeRequest) -> ScrapeResponse:
    scraper = ScraperService()
    return await scraper.scrape(payload)
