from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from app.api.routes import admin, interactions, news_article, news_feed, news_filter, reliability

app = FastAPI(title="FinSight News API")
UI_INDEX = Path(__file__).resolve().parent / "ui" / "index.html"

# Register routers - these will be implemented in Day 3/4
# For now, we just include them so the structure is ready
app.include_router(news_feed.router, prefix="/api/v1/news", tags=["news"])
app.include_router(news_filter.router, prefix="/api/v1/news", tags=["news"])
app.include_router(news_article.router, prefix="/api/v1/news", tags=["news"])
app.include_router(reliability.router, prefix="/api/v1/reliability", tags=["reliability"])
app.include_router(reliability.router, prefix="/api/v1/news/reliability", tags=["reliability"])
app.include_router(interactions.router, prefix="/api/v1/interactions", tags=["interactions"])
app.include_router(interactions.router, prefix="/api/v1/news", tags=["interactions"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/ui")


@app.get("/ui", include_in_schema=False)
async def minimal_ui() -> FileResponse:
    return FileResponse(UI_INDEX)
