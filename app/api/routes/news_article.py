from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db_session
from app.models.schemas import NewsArticle, NewsSentimentAnalysis, NewsStockTag, NewsSectorTag, SourceReliabilityStats
from app.models.api_models import NewsArticleResponse
from uuid import UUID

router = APIRouter()

@router.get("/{article_id}", response_model=NewsArticleResponse)
async def get_article_details(
    article_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Fetch full metadata and analysis for a specific article."""
    
    # Get Article & Analysis
    query = (
        select(NewsArticle, NewsSentimentAnalysis, SourceReliabilityStats.accuracy_24h)
        .outerjoin(NewsSentimentAnalysis, NewsArticle.id == NewsSentimentAnalysis.article_id)
        .outerjoin(SourceReliabilityStats, NewsArticle.source_name == SourceReliabilityStats.source_name)
        .where(NewsArticle.id == article_id)
    )
    
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Article not found")
        
    art, analysis, source_rel = row
    
    # Get Tags
    ticker_result = await db.execute(select(NewsStockTag.ticker).where(NewsStockTag.article_id == art.id))
    sector_result = await db.execute(select(NewsSectorTag.sector_name).where(NewsSectorTag.article_id == art.id))
    
    return NewsArticleResponse(
        id=str(art.id),
        title=art.title,
        source_name=art.source_name,
        source_url=art.source_url,
        published_at=art.published_at,
        summary=art.summary,
        image_url=art.image_url,
        sentiment_label=analysis.sentiment_label if analysis else None,
        sentiment_score=analysis.sentiment_score if analysis else None,
        impact_level=analysis.impact_level if analysis else None,
        impact_score=analysis.impact_score if analysis else None,
        ai_explanation=analysis.ai_explanation if analysis else None,
        reliability_score=source_rel,
        tickers=[t[0] for t in ticker_result.all()],
        sectors=[s[0] for s in sector_result.all()]
    )


@router.get("/article/{article_id}", response_model=NewsArticleResponse)
async def get_article_details_alias(
    article_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Alias for plan-compatible path: GET /api/v1/news/article/{id}."""
    return await get_article_details(article_id, db)
