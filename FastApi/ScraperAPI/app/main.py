from fastapi import FastAPI

from app.database import init_database
from app.routes import extract, health, research, scrape


app = FastAPI(
    title="ScraperAPI",
    description="API de pesquisa, web scraping e organizacao local de informacoes.",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_database()


app.include_router(health.router)
app.include_router(scrape.router)
app.include_router(extract.router)
app.include_router(research.router)
