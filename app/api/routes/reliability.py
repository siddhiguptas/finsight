from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import case, desc, func, select
from app.core.database import get_db_session
from app.models.schemas import ModelReliabilityStats, NewsReliabilityScore, SourceReliabilityStats

router = APIRouter()

@router.get("/sources")
async def get_source_reliability(
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session)
):
    """Get credibility stats for news sources (e.g. SeekingAlpha vs NewsAPI)."""
    result = await db.execute(
        select(SourceReliabilityStats).order_by(desc(SourceReliabilityStats.accuracy_24h)).limit(limit)
    )
    return result.scalars().all()


@router.get("/source/{source_name}")
async def get_source_reliability_detail(
    source_name: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Return reliability stats for a specific news source."""
    result = await db.execute(
        select(SourceReliabilityStats).where(SourceReliabilityStats.source_name == source_name)
    )
    stats = result.scalar_one_or_none()
    if not stats:
        raise HTTPException(status_code=404, detail="Source not found")

    accuracy_24h = stats.accuracy_24h or 0.0
    if accuracy_24h >= 0.7:
        tier = "HIGH"
    elif accuracy_24h >= 0.55:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    return {
        "source_name": stats.source_name,
        "total_articles_scored": stats.total_articles or 0,
        "accuracy_24h": stats.accuracy_24h,
        "accuracy_72h": stats.accuracy_72h,
        "avg_impact_score": stats.avg_impact_score,
        "reliability_tier": tier,
        "last_updated": stats.last_updated,
    }


@router.get("/ticker/{ticker}")
async def get_ticker_reliability(
    ticker: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Return rolling reliability stats for a specific ticker."""
    ticker = ticker.upper()

    total_res = await db.execute(
        select(func.count(NewsReliabilityScore.id)).where(NewsReliabilityScore.ticker == ticker)
    )
    total = total_res.scalar() or 0
    if total == 0:
        raise HTTPException(status_code=404, detail="Ticker not found")

    correct_24_res = await db.execute(
        select(func.count(NewsReliabilityScore.id)).where(
            NewsReliabilityScore.ticker == ticker,
            NewsReliabilityScore.prediction_correct_24h == True,
        )
    )
    correct_24 = correct_24_res.scalar() or 0

    correct_72_res = await db.execute(
        select(func.count(NewsReliabilityScore.id)).where(
            NewsReliabilityScore.ticker == ticker,
            NewsReliabilityScore.prediction_correct_72h == True,
        )
    )
    correct_72 = correct_72_res.scalar() or 0

    by_sentiment_res = await db.execute(
        select(
            NewsReliabilityScore.sentiment_predicted,
            func.count(NewsReliabilityScore.id).label("count"),
            func.sum(
                case(
                    (NewsReliabilityScore.prediction_correct_24h == True, 1),
                    else_=0,
                )
            ).label("correct"),
        )
        .where(NewsReliabilityScore.ticker == ticker)
        .group_by(NewsReliabilityScore.sentiment_predicted)
    )

    by_sentiment = {}
    for sentiment, count, correct in by_sentiment_res.all():
        by_sentiment[sentiment] = {
            "accuracy_24h": (correct or 0) / count if count else 0.0,
            "count": count,
        }

    return {
        "ticker": ticker,
        "total_predictions": total,
        "correct_24h": correct_24,
        "accuracy_24h": correct_24 / total if total else 0.0,
        "correct_72h": correct_72,
        "accuracy_72h": correct_72 / total if total else 0.0,
        "by_sentiment": by_sentiment,
    }

@router.get("/models")
async def get_model_reliability(
    db: AsyncSession = Depends(get_db_session)
):
    """Get accuracy stats for the AI models (FinBERT vs Gemini)."""
    result = await db.execute(select(ModelReliabilityStats))
    return result.scalars().all()
