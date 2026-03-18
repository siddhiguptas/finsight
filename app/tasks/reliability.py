import asyncio
from datetime import datetime, timedelta

import yfinance as yf
from celery import shared_task
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.schemas import (
    NewsArticle,
    NewsSentimentAnalysis,
    NewsReliabilityScore,
    NewsStockTag,
    SourceReliabilityStats,
)


async def fetch_historical_price(ticker: str, timestamp: datetime):
    """Fetch the first available close price on/after the timestamp using yfinance."""
    try:
        start_date = timestamp.date()
        end_date = (timestamp + timedelta(days=3)).date()
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            return None
        return float(data.iloc[0]["Close"])
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return None


def movement_direction(pct_change: float | None) -> str | None:
    if pct_change is None:
        return None
    if pct_change > 0.005:
        return "UP"
    if pct_change < -0.005:
        return "DOWN"
    return "FLAT"


def prediction_correct(sentiment_label: str, pct_change: float | None) -> bool | None:
    if pct_change is None:
        return None
    if sentiment_label == "POSITIVE":
        return pct_change > 0.005
    if sentiment_label == "NEGATIVE":
        return pct_change < -0.005
    if sentiment_label == "NEUTRAL":
        return abs(pct_change) <= 0.005
    return None


async def run_reliability_check():
    """
    Nightly backtest:
    1) Select articles ~24h old with primary ticker tags.
    2) Compare predicted sentiment vs 24h/72h price movement.
    3) Store per-article reliability and update source aggregates.
    """
    now = datetime.utcnow()
    window_start = now - timedelta(hours=26)
    window_end = now - timedelta(hours=22)

    async with AsyncSessionLocal() as session:
        stmt = (
            select(NewsArticle, NewsSentimentAnalysis, NewsStockTag.ticker)
            .join(NewsStockTag, NewsArticle.id == NewsStockTag.article_id)
            .join(
                NewsSentimentAnalysis,
                (NewsSentimentAnalysis.article_id == NewsArticle.id)
                & (NewsSentimentAnalysis.ticker == NewsStockTag.ticker),
            )
            .where(NewsArticle.published_at.between(window_start, window_end))
            .where(NewsStockTag.is_primary == True)
        )

        result = await session.execute(stmt)
        rows = result.all()

        for article, analysis, ticker in rows:
            # Skip if already scored for this article+ticker
            existing = await session.execute(
                select(NewsReliabilityScore.id).where(
                    NewsReliabilityScore.article_id == article.id,
                    NewsReliabilityScore.ticker == ticker,
                )
            )
            if existing.scalar_one_or_none():
                continue

            p_start = await fetch_historical_price(ticker, article.published_at)
            p_24 = await fetch_historical_price(ticker, article.published_at + timedelta(hours=24))
            p_72 = await fetch_historical_price(ticker, article.published_at + timedelta(hours=72))

            if p_start is None or p_24 is None:
                continue

            pct_24 = (p_24 - p_start) / p_start
            pct_72 = (p_72 - p_start) / p_start if p_72 is not None else None

            correct_24 = prediction_correct(analysis.sentiment_label, pct_24)
            correct_72 = prediction_correct(analysis.sentiment_label, pct_72)

            score = NewsReliabilityScore(
                sentiment_analysis_id=analysis.id,
                article_id=article.id,
                ticker=ticker,
                sentiment_predicted=analysis.sentiment_label,
                price_at_publish=p_start,
                price_24h_later=p_24,
                price_72h_later=p_72,
                actual_movement_24h=pct_24,
                actual_movement_72h=pct_72,
                movement_direction_24h=movement_direction(pct_24),
                movement_direction_72h=movement_direction(pct_72),
                prediction_correct_24h=correct_24,
                prediction_correct_72h=correct_72,
                reliability_score=1.0 if correct_24 else 0.0,
                backtested_at=now,
            )
            session.add(score)

            # Update aggregate stats for the source
            stats_res = await session.execute(
                select(SourceReliabilityStats).where(
                    SourceReliabilityStats.source_name == article.source_name
                )
            )
            stats = stats_res.scalar_one_or_none()
            if not stats:
                stats = SourceReliabilityStats(source_name=article.source_name)
                session.add(stats)

            total_articles = (stats.total_articles or 0) + 1
            stats.total_articles = total_articles

            stats.correct_24h = (stats.correct_24h or 0) + (1 if correct_24 else 0)
            stats.accuracy_24h = stats.correct_24h / total_articles

            if correct_72 is not None:
                stats.correct_72h = (stats.correct_72h or 0) + (1 if correct_72 else 0)
                stats.accuracy_72h = stats.correct_72h / total_articles

            # rolling average impact score
            prev_avg = stats.avg_impact_score or 0.0
            stats.avg_impact_score = ((prev_avg * (total_articles - 1)) + analysis.impact_score) / total_articles
            stats.last_updated = now

        await session.commit()


@shared_task(name="app.tasks.reliability.run_nightly_backtest")
def run_nightly_backtest():
    asyncio.run(run_reliability_check())
    return {"status": "success"}
