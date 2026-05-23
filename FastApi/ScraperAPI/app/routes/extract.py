from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.schemas import ExtractRequest, ExtractResponse
from app.services.extractor import ExtractorService


router = APIRouter(prefix="/extract", tags=["extract"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=ExtractResponse)
def extract_html(payload: ExtractRequest) -> ExtractResponse:
    extractor = ExtractorService()
    return extractor.extract(
        html=payload.html,
        url=payload.url,
        include_text=payload.include_text,
        include_links=payload.include_links,
    )
