from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.auth import get_current_user
from app.models.api_models import NewsArticleResponse, NewsFeedResponse
from app.models.schemas import (
    NewsArticle,
    NewsReliabilityScore,
    NewsSectorTag,
    NewsSentimentAnalysis,
    NewsStockTag,
    SourceReliabilityStats,
    UserWatchlist,
)

router = APIRouter()


def parse_ticker_list(tickers_str: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated ticker string into a list of tickers."""
    if tickers_str is None:
        return None
    # Split by comma and strip whitespace
    return [t.strip().upper() for t in tickers_str.split(',') if t.strip()]

@router.get("/feed", response_model=NewsFeedResponse)
async def get_news_feed(
    tier: str = Query("general", enum=["portfolio", "sector", "general", "market"]),
    tickers: Optional[str] = Query(None, description="Comma-separated list of stock tickers"),
    sector: Optional[str] = Query(None),
    user_id: Optional[UUID] = Query(None),
    impact_level: Optional[str] = Query(None, enum=["HIGH", "MEDIUM", "LOW"]),
    time_window: Optional[int] = Query(None, ge=1, le=168),
    min_reliability: Optional[float] = Query(None, ge=0.0, le=1.0),
    sentiment: Optional[str] = Query(None, enum=["POSITIVE", "NEGATIVE", "NEUTRAL"]),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get news feed based on tiers.
    - general/market: General high-impact news.
    - portfolio: News for specific tickers. If no tickers provided, use user's watchlist.
    - sector: News for a specific industry/sector.
    """
    # Parse comma-separated tickers into a list
    target_tickers = parse_ticker_list(tickers)
    if tier == "market":
        tier = "general"

    # Base query joining Article, Analysis, and Tags
    query = (
        select(
            NewsArticle,
            NewsSentimentAnalysis,
            NewsReliabilityScore.reliability_score,
            SourceReliabilityStats.accuracy_24h,
        )
        .outerjoin(NewsSentimentAnalysis, NewsArticle.id == NewsSentimentAnalysis.article_id)
        .outerjoin(NewsReliabilityScore, NewsArticle.id == NewsReliabilityScore.article_id)
        .outerjoin(SourceReliabilityStats, NewsArticle.source_name == SourceReliabilityStats.source_name)
        .where(NewsArticle.is_deleted == False)
        .where(NewsArticle.is_duplicate == False)
    )

    if tier == "portfolio":
        if not target_tickers and user_id:
            # Fetch from watchlist
            res = await db.execute(select(UserWatchlist.ticker).where(UserWatchlist.user_id == user_id))
            target_tickers = [r[0] for r in res.all()]

        if not target_tickers:
            # If no tickers found, return empty response instead of error
            return NewsFeedResponse(articles=[], count=0, tier="portfolio")
            
        query = query.join(NewsStockTag, NewsArticle.id == NewsStockTag.article_id).where(NewsStockTag.ticker.in_(target_tickers))

    
    elif tier == "sector":
        if not sector:
            raise HTTPException(status_code=400, detail="Sector name required for sector tier")
        query = query.join(NewsSectorTag, NewsArticle.id == NewsSectorTag.article_id).where(NewsSectorTag.sector_name.ilike(f"%{sector}%"))

    if impact_level:
        query = query.where(NewsSentimentAnalysis.impact_level == impact_level)

    if sentiment:
        query = query.where(NewsSentimentAnalysis.sentiment_label == sentiment)

    if time_window:
        since = datetime.utcnow() - timedelta(hours=time_window)
        query = query.where(NewsArticle.published_at >= since)

    if min_reliability is not None and min_reliability > 0:
        rel_score = func.coalesce(NewsReliabilityScore.reliability_score, SourceReliabilityStats.accuracy_24h)
        query = query.where(rel_score >= min_reliability)
    
    # Order by impact score and date
    query = query.order_by(desc(NewsSentimentAnalysis.impact_score), desc(NewsArticle.published_at))

    fetch_limit = limit + offset + 50
    result = await db.execute(query.limit(fetch_limit))
    rows = result.all()

    articles_response = []
    seen = set()
    skipped = 0
    for art, analysis, rel_score, source_rel in rows:
        if art.id in seen:
            continue
        seen.add(art.id)

        if skipped < offset:
            skipped += 1
            continue

        if len(articles_response) >= limit:
            break

        # Fetch associated tickers and sectors for each article
        # (Optimized approach would use subqueries or selectinload, but for MVP this is clear)
        ticker_result = await db.execute(select(NewsStockTag.ticker).where(NewsStockTag.article_id == art.id))
        sector_result = await db.execute(select(NewsSectorTag.sector_name).where(NewsSectorTag.article_id == art.id))
        
        art_resp = NewsArticleResponse(
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
            reliability_score=rel_score if rel_score is not None else source_rel,
            tickers=[t[0] for t in ticker_result.all()],
            sectors=[s[0] for s in sector_result.all()]
        )
        articles_response.append(art_resp)

    return NewsFeedResponse(
        articles=articles_response,
        count=len(articles_response),
        tier=tier
    )


@router.get("/watchlist-feed", response_model=NewsFeedResponse)
async def get_watchlist_feed(
    user_id: UUID,
    impact_level: Optional[str] = Query(None, enum=["HIGH", "MEDIUM", "LOW"]),
    time_window: Optional[int] = Query(None, ge=1, le=168),
    min_reliability: Optional[float] = Query(None, ge=0.0, le=1.0),
    sentiment: Optional[str] = Query(None, enum=["POSITIVE", "NEGATIVE", "NEUTRAL"]),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user)
):
    """News feed for a user's watchlist (alias of portfolio tier)."""
    return await get_news_feed(
        tier="portfolio",
        user_id=user_id,
        impact_level=impact_level,
        time_window=time_window,
        min_reliability=min_reliability,
        sentiment=sentiment,
        limit=limit,
        offset=offset,
        db=db,
    )
