from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse

from app.api.routes.live_news import router as live_news_router

app = FastAPI(
    title="FinSight News API",
    description="Real-time financial news fetcher with optional ML analysis",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

UI_INDEX = Path(__file__).resolve().parent / "ui" / "index.html"

app.include_router(live_news_router, prefix="/api/v1/news", tags=["news"])


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/ui")


@app.get("/ui", include_in_schema=False)
async def minimal_ui() -> FileResponse:
    return FileResponse(UI_INDEX)
