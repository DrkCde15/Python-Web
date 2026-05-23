from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_api_key
from app.repositories.research_repository import ResearchRepository
from app.schemas import ResearchRequest, ResearchResponse
from app.services.research import ResearchService


router = APIRouter(prefix="/research", tags=["research"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=ResearchResponse)
async def create_research(payload: ResearchRequest) -> ResearchResponse:
    service = ResearchService()
    return await service.run(payload)


@router.get("/{research_id}", response_model=ResearchResponse)
def get_research(research_id: str) -> ResearchResponse:
    repository = ResearchRepository()
    research = repository.get(research_id)
    if research is None:
        raise HTTPException(status_code=404, detail="Pesquisa nao encontrada.")
    return research


@router.get("/{research_id}/report", response_model=dict[str, str])
def get_research_report(research_id: str) -> dict[str, str]:
    repository = ResearchRepository()
    report = repository.get_report(research_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Pesquisa nao encontrada.")
    return {"research_id": research_id, "format": "markdown", "content": report}
