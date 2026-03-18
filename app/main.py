from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.openapi.utils import get_openapi
from app.api.routes import admin, interactions, news_article, news_feed, news_filter, reliability
from app.api.routes.auth import router as auth_router
from app.core.auth import oauth2_scheme

app = FastAPI(
    title="FinSight News API",
    description="Financial news aggregation and analysis system with AI-powered sentiment analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

UI_INDEX = Path(__file__).resolve().parent / "ui" / "index.html"

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="FinSight News API",
        version="1.0.0",
        description="Financial news aggregation and analysis system with AI-powered sentiment analysis",
        routes=app.routes,
    )
    
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer Auth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT token. The token can be obtained from the authentication service."
        }
    }
    
    public_paths = ["/api/v1/auth/token", "/health", "/docs", "/openapi.json", "/redoc", "/ui"]
    
    for path, path_item in openapi_schema["paths"].items():
        if any(path.startswith(public) for public in public_paths):
            continue
        for method, method_item in path_item.items():
            if isinstance(method_item, dict) and "security" not in method_item:
                method_item["security"] = [{"Bearer Auth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])
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
