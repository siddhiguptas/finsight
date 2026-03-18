from uuid import UUID

from fastapi import APIRouter

router = APIRouter()


@router.post("/news/reprocess/{article_id}")
async def reprocess_article(article_id: UUID):
    """Admin-only: re-run NLP + sentiment pipeline for an article."""
    from app.tasks.process import process_article
    process_article.delay(str(article_id))
    return {"status": "queued", "article_id": str(article_id)}
