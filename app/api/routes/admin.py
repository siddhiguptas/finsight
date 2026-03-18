from uuid import UUID

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def get_status():
    """Admin-only: get system status."""
    return {
        "status": "operational",
        "services": {
            "api": "running",
            "celery": "running",
            "database": "connected"
        }
    }


@router.post("/ingest/trigger")
async def trigger_ingestion(source: str = "all"):
    """Admin-only: trigger news ingestion from specified source."""
    from app.tasks.ingest import fetch_newsapi, fetch_yahoo_rss, fetch_reddit, fetch_alpha_vantage, fetch_sec_edgar
    
    sources_map = {
        "newsapi": fetch_newsapi,
        "rss": fetch_yahoo_rss,
        "reddit": fetch_reddit,
        "alphavantage": fetch_alpha_vantage,
        "sec": fetch_sec_edgar,
        "all": None
    }
    
    if source not in sources_map:
        return {"error": f"Invalid source. Valid: {list(sources_map.keys())}"}
    
    triggered = []
    if source == "all":
        for src, task in sources_map.items():
            if src != "all":
                task.delay()
                triggered.append(src)
    else:
        sources_map[source].delay()
        triggered.append(source)
    
    return {
        "status": "queued",
        "triggered_sources": triggered,
        "message": "Ingestion tasks have been queued. Check Celery worker for progress."
    }


@router.post("/news/reprocess/{article_id}")
async def reprocess_article(article_id: UUID):
    """Admin-only: re-run NLP + sentiment pipeline for an article."""
    from app.tasks.process import process_article
    process_article.delay(str(article_id))
    return {"status": "queued", "article_id": str(article_id)}
