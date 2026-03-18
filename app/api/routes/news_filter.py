from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.api_models import NewsArticleResponse, NewsFeedResponse
from app.models.schemas import (
    NewsArticle,
    NewsReliabilityScore,
    NewsSectorTag,
    NewsSentimentAnalysis,
    NewsStockTag,
    SourceReliabilityStats,
)

router = APIRouter()


def _parse_csv(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    return items or None


@router.get("/filter", response_model=NewsFeedResponse)
async def filter_news(
    impact_level: Optional[str] = Query(None, enum=["HIGH", "MEDIUM", "LOW"]),
    time_window: Optional[int] = Query(24, ge=1, le=168),
    min_reliability: Optional[float] = Query(0.0, ge=0.0, le=1.0),
    sentiment: Optional[str] = Query(None, enum=["POSITIVE", "NEGATIVE", "NEUTRAL"]),
    tickers: Optional[str] = Query(None),
    sectors: Optional[str] = Query(None),
    sources: Optional[str] = Query(None),
    sort_by: str = Query("published_at", enum=["published_at", "impact_score", "reliability_score"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
):
    """Advanced filtering endpoint for the news feed UI."""
    ticker_list = _parse_csv(tickers)
    sector_list = _parse_csv(sectors)
    source_list = _parse_csv(sources)

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

    if ticker_list:
        query = query.join(NewsStockTag, NewsArticle.id == NewsStockTag.article_id).where(
            NewsStockTag.ticker.in_(ticker_list)
        )

    if sector_list:
        query = query.join(NewsSectorTag, NewsArticle.id == NewsSectorTag.article_id).where(
            NewsSectorTag.sector_name.in_(sector_list)
        )

    if source_list:
        query = query.where(NewsArticle.source_name.in_(source_list))

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

    sort_map = {
        "published_at": NewsArticle.published_at,
        "impact_score": NewsSentimentAnalysis.impact_score,
        "reliability_score": func.coalesce(
            NewsReliabilityScore.reliability_score, SourceReliabilityStats.accuracy_24h
        ),
    }
    sort_col = sort_map.get(sort_by, NewsArticle.published_at)
    sort_col = sort_col.asc() if sort_order == "asc" else sort_col.desc()
    query = query.order_by(sort_col, desc(NewsArticle.published_at))

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

        ticker_res = await db.execute(select(NewsStockTag.ticker).where(NewsStockTag.article_id == art.id))
        sector_res = await db.execute(select(NewsSectorTag.sector_name).where(NewsSectorTag.article_id == art.id))

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
            tickers=[t[0] for t in ticker_res.all()],
            sectors=[s[0] for s in sector_res.all()],
        )
        articles_response.append(art_resp)

    return NewsFeedResponse(articles=articles_response, count=len(articles_response), tier="filter")


@router.get("/search", response_model=NewsFeedResponse)
async def search_news(
    q: str = Query(...),
    sentiment: Optional[str] = Query(None, enum=["POSITIVE", "NEGATIVE", "NEUTRAL"]),
    min_impact: float = Query(0.0, ge=0.0, le=1.0),
    min_reliability: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
):
    """Search articles by text, sentiment, impact, and source reliability."""
    query = (
        select(NewsArticle, NewsSentimentAnalysis)
        .join(NewsSentimentAnalysis, NewsArticle.id == NewsSentimentAnalysis.article_id)
        .outerjoin(SourceReliabilityStats, NewsArticle.source_name == SourceReliabilityStats.source_name)
        .where(NewsArticle.title.ilike(f"%{q}%"))
    )

    if sentiment:
        query = query.where(NewsSentimentAnalysis.sentiment_label == sentiment)

    if min_impact > 0:
        query = query.where(NewsSentimentAnalysis.impact_score >= min_impact)

    if min_reliability > 0:
        query = query.where(SourceReliabilityStats.accuracy_24h >= min_reliability)

    query = query.order_by(desc(NewsArticle.published_at)).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    articles_response = []
    for art, analysis in rows:
        ticker_res = await db.execute(select(NewsStockTag.ticker).where(NewsStockTag.article_id == art.id))
        sector_res = await db.execute(select(NewsSectorTag.sector_name).where(NewsSectorTag.article_id == art.id))

        art_resp = NewsArticleResponse(
            id=str(art.id),
            title=art.title,
            source_name=art.source_name,
            source_url=art.source_url,
            published_at=art.published_at,
            summary=art.summary,
            image_url=art.image_url,
            sentiment_label=analysis.sentiment_label,
            sentiment_score=analysis.sentiment_score,
            impact_level=analysis.impact_level,
            impact_score=analysis.impact_score,
            ai_explanation=analysis.ai_explanation,
            tickers=[t[0] for t in ticker_res.all()],
            sectors=[s[0] for s in sector_res.all()],
        )
        articles_response.append(art_resp)

    return NewsFeedResponse(articles=articles_response, count=len(articles_response), tier="search")
