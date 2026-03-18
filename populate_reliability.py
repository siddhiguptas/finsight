#!/usr/bin/env python3
"""
Populate sample reliability data for testing the reliability API routes.
This simulates what the nightly backtest would produce.
"""
import asyncio
import uuid
from datetime import datetime, timedelta

from app.core.database import AsyncSessionLocal
from app.models.schemas import (
    SourceReliabilityStats,
    NewsReliabilityScore,
)


async def populate_reliability_data():
    async with AsyncSessionLocal() as db:
        print("Creating source reliability stats...")
        
        # Create source reliability stats
        sources = [
            SourceReliabilityStats(
                source_name="newsapi",
                total_articles=1500,
                correct_24h=1150,
                correct_72h=1050,
                accuracy_24h=0.77,
                accuracy_72h=0.70,
                avg_impact_score=0.72,
                last_updated=datetime.utcnow()
            ),
            SourceReliabilityStats(
                source_name="rss",
                total_articles=800,
                correct_24h=560,
                correct_72h=520,
                accuracy_24h=0.70,
                accuracy_72h=0.65,
                avg_impact_score=0.68,
                last_updated=datetime.utcnow()
            ),
            SourceReliabilityStats(
                source_name="reddit",
                total_articles=2000,
                correct_24h=1100,
                correct_72h=1000,
                accuracy_24h=0.55,
                accuracy_72h=0.50,
                avg_impact_score=0.55,
                last_updated=datetime.utcnow()
            ),
            SourceReliabilityStats(
                source_name="alphavantage",
                total_articles=500,
                correct_24h=400,
                correct_72h=380,
                accuracy_24h=0.80,
                accuracy_72h=0.76,
                avg_impact_score=0.78,
                last_updated=datetime.utcnow()
            ),
            SourceReliabilityStats(
                source_name="sec",
                total_articles=200,
                correct_24h=160,
                correct_72h=150,
                accuracy_24h=0.80,
                accuracy_72h=0.75,
                avg_impact_score=0.82,
                last_updated=datetime.utcnow()
            ),
        ]
        
        for s in sources:
            # Use merge to update if exists, insert if not
            await db.merge(s)
        await db.commit()
        
        print(f"✅ Created {len(sources)} source reliability stats")
        
        print("\nCreating article reliability scores...")
        
        # Create sample article reliability scores
        scores = [
            # NewsAPI - mostly correct
            NewsReliabilityScore(
                sentiment_analysis_id=uuid.uuid4(),
                article_id=uuid.uuid4(),
                ticker="AAPL",
                sentiment_predicted="POSITIVE",
                price_at_publish=175.50,
                price_24h_later=178.25,
                price_72h_later=180.00,
                actual_movement_24h=0.0157,
                actual_movement_72h=0.0256,
                movement_direction_24h="UP",
                movement_direction_72h="UP",
                prediction_correct_24h=True,
                prediction_correct_72h=True,
                reliability_score=0.85,
                backtested_at=datetime.utcnow() - timedelta(hours=2)
            ),
            NewsReliabilityScore(
                sentiment_analysis_id=uuid.uuid4(),
                article_id=uuid.uuid4(),
                ticker="MSFT",
                sentiment_predicted="POSITIVE",
                price_at_publish=350.00,
                price_24h_later=355.50,
                price_72h_later=352.00,
                actual_movement_24h=0.0157,
                actual_movement_72h=0.0057,
                movement_direction_24h="UP",
                movement_direction_72h="UP",
                prediction_correct_24h=True,
                prediction_correct_72h=True,
                reliability_score=0.90,
                backtested_at=datetime.utcnow() - timedelta(hours=2)
            ),
            NewsReliabilityScore(
                sentiment_analysis_id=uuid.uuid4(),
                article_id=uuid.uuid4(),
                ticker="TSLA",
                sentiment_predicted="NEGATIVE",
                price_at_publish=245.00,
                price_24h_later=238.00,
                price_72h_later=230.00,
                actual_movement_24h=-0.0286,
                actual_movement_72h=-0.0612,
                movement_direction_24h="DOWN",
                movement_direction_72h="DOWN",
                prediction_correct_24h=True,
                prediction_correct_72h=True,
                reliability_score=0.95,
                backtested_at=datetime.utcnow() - timedelta(hours=2)
            ),
            # RSS - mixed
            NewsReliabilityScore(
                sentiment_analysis_id=uuid.uuid4(),
                article_id=uuid.uuid4(),
                ticker="SPY",
                sentiment_predicted="NEUTRAL",
                price_at_publish=450.00,
                price_24h_later=450.50,
                price_72h_later=449.00,
                actual_movement_24h=0.0011,
                actual_movement_72h=-0.0022,
                movement_direction_24h="FLAT",
                movement_direction_72h="FLAT",
                prediction_correct_24h=True,
                prediction_correct_72h=True,
                reliability_score=0.75,
                backtested_at=datetime.utcnow() - timedelta(hours=2)
            ),
            # Reddit - lower accuracy
            NewsReliabilityScore(
                sentiment_analysis_id=uuid.uuid4(),
                article_id=uuid.uuid4(),
                ticker="NVDA",
                sentiment_predicted="POSITIVE",
                price_at_publish=450.00,
                price_24h_later=440.00,
                price_72h_later=435.00,
                actual_movement_24h=-0.0222,
                actual_movement_72h=-0.0333,
                movement_direction_24h="DOWN",
                movement_direction_72h="DOWN",
                prediction_correct_24h=False,
                prediction_correct_72h=False,
                reliability_score=0.30,
                backtested_at=datetime.utcnow() - timedelta(hours=2)
            ),
            NewsReliabilityScore(
                sentiment_analysis_id=uuid.uuid4(),
                article_id=uuid.uuid4(),
                ticker="GOOGL",
                sentiment_predicted="POSITIVE",
                price_at_publish=140.00,
                price_24h_later=142.50,
                price_72h_later=141.00,
                actual_movement_24h=0.0179,
                actual_movement_72h=0.0071,
                movement_direction_24h="UP",
                movement_direction_72h="UP",
                prediction_correct_24h=True,
                prediction_correct_72h=True,
                reliability_score=0.88,
                backtested_at=datetime.utcnow() - timedelta(hours=2)
            ),
        ]
        
        for s in scores:
            db.add(s)
        await db.commit()
        
        print(f"✅ Created {len(scores)} article reliability scores")
        
        print("\n" + "="*60)
        print("Reliability data population complete!")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(populate_reliability_data())
