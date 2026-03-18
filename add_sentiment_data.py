#!/usr/bin/env python3
"""Add mock sentiment and sector data to existing articles for testing filters."""
import asyncio
from datetime import datetime
from app.core.database import AsyncSessionLocal
from app.models.schemas import NewsSentimentAnalysis, NewsSectorTag

async def add_test_data():
    async with AsyncSessionLocal() as db:
        print("Adding sentiment and sector data...")
        
        # Article 1: 3M industrial - POSITIVE, HIGH impact
        db.add(NewsSentimentAnalysis(
            article_id="2acb1916-c0e7-4498-a9e7-9221afa4388b",
            ticker="MMM", 
            sentiment_label="POSITIVE", 
            sentiment_score=0.72,
            positive_score=0.80, neutral_score=0.15, negative_score=0.05,
            impact_level="HIGH", 
            impact_score=0.78, 
            ai_model_used="mock", 
            analyzed_at=datetime.utcnow()
        ))
        db.add(NewsSectorTag(article_id="2acb1916-c0e7-4498-a9e7-9221afa4388b", sector_name="Industrials"))
        
        # Article 2: Perplexity/AAPL - POSITIVE, HIGH impact
        db.add(NewsSentimentAnalysis(
            article_id="2470fe11-5468-4960-82d5-ad13878e9a35",
            ticker="AAPL", 
            sentiment_label="POSITIVE", 
            sentiment_score=0.85,
            positive_score=0.88, neutral_score=0.10, negative_score=0.02,
            impact_level="HIGH", 
            impact_score=0.88, 
            ai_model_used="mock", 
            analyzed_at=datetime.utcnow()
        ))
        db.add(NewsSectorTag(article_id="2470fe11-5468-4960-82d5-ad13878e9a35", sector_name="Technology"))
        
        # Article 3: Sokoto - NEUTRAL, LOW impact
        db.add(NewsSentimentAnalysis(
            article_id="dcc8ffbe-53b4-48be-aeb4-f29a6877eb98",
            ticker=None, 
            sentiment_label="NEUTRAL", 
            sentiment_score=0.05,
            positive_score=0.10, neutral_score=0.80, negative_score=0.10,
            impact_level="LOW", 
            impact_score=0.35, 
            ai_model_used="mock", 
            analyzed_at=datetime.utcnow()
        ))
        
        # Article 4: ECWA kidnappers - NEGATIVE, MEDIUM impact
        db.add(NewsSentimentAnalysis(
            article_id="9302ad67-7501-4f9d-9f1c-9dd6d2a72ef7",
            ticker=None, 
            sentiment_label="NEGATIVE", 
            sentiment_score=-0.55,
            positive_score=0.05, neutral_score=0.30, negative_score=0.65,
            impact_level="MEDIUM", 
            impact_score=0.42, 
            ai_model_used="mock", 
            analyzed_at=datetime.utcnow()
        ))
        
        # Article 5: GTA 6 - NEUTRAL, MEDIUM impact
        db.add(NewsSentimentAnalysis(
            article_id="f79abe22-63b2-4897-9cd1-372586ad843a",
            ticker="TTWO", 
            sentiment_label="NEUTRAL", 
            sentiment_score=0.10,
            positive_score=0.15, neutral_score=0.70, negative_score=0.15,
            impact_level="MEDIUM", 
            impact_score=0.45, 
            ai_model_used="mock", 
            analyzed_at=datetime.utcnow()
        ))
        db.add(NewsSectorTag(article_id="f79abe22-63b2-4897-9cd1-372586ad843a", sector_name="Gaming"))
        
        await db.commit()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(add_test_data())
