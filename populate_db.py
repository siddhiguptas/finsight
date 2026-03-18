#!/usr/bin/env python3
"""Populate the database with sample news articles for testing."""
import asyncio
import uuid
import hashlib
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.schemas import (
    NewsArticle,
    NewsSentimentAnalysis,
    NewsReliabilityScore,
    SourceReliabilityStats,
    NewsStockTag,
    NewsSectorTag,
)


def generate_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def populate_sample_data():
    async with AsyncSessionLocal() as db:
        print("Creating source reliability stats...")
        
        # Create source reliability stats
        sources = [
            SourceReliabilityStats(
                source_name="newsapi",
                total_articles=1500,
                accuracy_24h=0.82,
                avg_impact_score=0.78,
                last_updated=datetime.utcnow()
            ),
            SourceReliabilityStats(
                source_name="rss",
                total_articles=800,
                accuracy_24h=0.75,
                avg_impact_score=0.70,
                last_updated=datetime.utcnow()
            ),
            SourceReliabilityStats(
                source_name="reddit",
                total_articles=2000,
                accuracy_24h=0.65,
                avg_impact_score=0.60,
                last_updated=datetime.utcnow()
            ),
            SourceReliabilityStats(
                source_name="alphavantage",
                total_articles=500,
                accuracy_24h=0.85,
                avg_impact_score=0.80,
                last_updated=datetime.utcnow()
            ),
        ]
        db.add_all(sources)
        await db.commit()
        
        print("Creating sample articles...")
        
        # Sample articles data
        articles_data = [
            {
                "title": "Apple Reports Record Q4 Earnings, Beats Expectations",
                "summary": "Apple Inc. reported record fourth quarter earnings, beating analyst expectations with strong iPhone and Services revenue growth.",
                "source_name": "newsapi",
                "source_url": "https://example.com/apple-earnings-q4",
                "published_at": datetime.utcnow() - timedelta(hours=2),
                "tickers": ["AAPL"],
                "sentiment": "POSITIVE",
                "sentiment_score": 0.85,
                "impact_score": 0.88,
                "sector": "Technology"
            },
            {
                "title": "Microsoft Azure Cloud Revenue Grows 29% Year-Over-Year",
                "summary": "Microsoft Azure continues to gain market share in cloud computing with 29% year-over-year revenue growth.",
                "source_name": "newsapi",
                "source_url": "https://example.com/msft-azure-growth",
                "published_at": datetime.utcnow() - timedelta(hours=4),
                "tickers": ["MSFT"],
                "sentiment": "POSITIVE",
                "sentiment_score": 0.78,
                "impact_score": 0.82,
                "sector": "Technology"
            },
            {
                "title": "Federal Reserve Signals Pause in Interest Rate Hikes",
                "summary": "The Federal Reserve signals a pause in interest rate hikes, providing relief to markets amid inflation concerns.",
                "source_name": "rss",
                "source_url": "https://example.com/fed-rate-pause",
                "published_at": datetime.utcnow() - timedelta(hours=6),
                "tickers": ["SPY", "QQQ"],
                "sentiment": "NEUTRAL",
                "sentiment_score": 0.02,
                "impact_score": 0.95,
                "sector": "Financial Markets"
            },
            {
                "title": "Tesla Faces Increasing Competition from Chinese EV Makers",
                "summary": "Tesla faces intensifying competition from Chinese electric vehicle manufacturers including BYD and NIO.",
                "source_name": "reddit",
                "source_url": "https://example.com/tesla-china-competition",
                "published_at": datetime.utcnow() - timedelta(hours=8),
                "tickers": ["TSLA"],
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.65,
                "impact_score": 0.72,
                "sector": "Automotive"
            },
            {
                "title": "NVIDIA Reports Unprecedented Demand for AI Training Chips",
                "summary": "NVIDIA reports unprecedented demand for AI training GPUs, with data center revenue hitting new highs.",
                "source_name": "newsapi",
                "source_url": "https://example.com/nvidia-ai-demand",
                "published_at": datetime.utcnow() - timedelta(hours=1),
                "tickers": ["NVDA"],
                "sentiment": "POSITIVE",
                "sentiment_score": 0.92,
                "impact_score": 0.90,
                "sector": "Technology"
            },
            {
                "title": "Amazon Web Services Launches New AI-Powered Analytics Tools",
                "summary": "AWS announces new AI-powered analytics tools to help businesses derive insights from their data.",
                "source_name": "newsapi",
                "source_url": "https://example.com/aws-ai-analytics",
                "published_at": datetime.utcnow() - timedelta(hours=3),
                "tickers": ["AMZN"],
                "sentiment": "POSITIVE",
                "sentiment_score": 0.70,
                "impact_score": 0.75,
                "sector": "Technology"
            },
            {
                "title": "Oil Prices Surge Amid Middle East Tensions",
                "summary": "Crude oil prices surge as geopolitical tensions in the Middle East raise supply concerns.",
                "source_name": "rss",
                "source_url": "https://example.com/oil-prices-surge",
                "published_at": datetime.utcnow() - timedelta(hours=5),
                "tickers": ["XOM", "CVX"],
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.45,
                "impact_score": 0.80,
                "sector": "Energy"
            },
            {
                "title": "JPMorgan CEO Jamie Dimon Warns of Economic Headwinds",
                "summary": "JPMorgan CEO Jamie Dimon warns of significant economic headwinds despite strong quarterly results.",
                "source_name": "newsapi",
                "source_url": "https://example.com/jpm-dimon-warning",
                "published_at": datetime.utcnow() - timedelta(hours=7),
                "tickers": ["JPM"],
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.55,
                "impact_score": 0.78,
                "sector": "Financial Services"
            },
            {
                "title": "Google Unveils New Gemini AI Model with Advanced Capabilities",
                "summary": "Google announces Gemini AI model, claiming breakthrough capabilities in reasoning and multimodal tasks.",
                "source_name": "newsapi",
                "source_url": "https://example.com/google-gemini",
                "published_at": datetime.utcnow() - timedelta(hours=2),
                "tickers": ["GOOGL"],
                "sentiment": "POSITIVE",
                "sentiment_score": 0.75,
                "impact_score": 0.85,
                "sector": "Technology"
            },
            {
                "title": "Boeing 737 Max Production Faces New Regulatory Scrutiny",
                "summary": "FAA announces new regulatory scrutiny on Boeing 737 Max production following quality concerns.",
                "source_name": "rss",
                "source_url": "https://example.com/boeing-scrutiny",
                "published_at": datetime.utcnow() - timedelta(hours=10),
                "tickers": ["BA"],
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.70,
                "impact_score": 0.65,
                "sector": "Aerospace"
            }
        ]
        
        created_articles = []
        
        for data in articles_data:
            content_for_hash = f"{data['title']}{data['summary']}{data['published_at']}"
            
            article = NewsArticle(
                id=uuid.uuid4(),
                external_id=str(uuid.uuid4()),
                source_name=data["source_name"],
                source_url=data["source_url"],
                title=data["title"],
                summary=data["summary"],
                published_at=data["published_at"],
                content_hash=generate_content_hash(content_for_hash),
                source_credibility_score=0.75,
                is_duplicate=False,
                is_deleted=False
            )
            db.add(article)
            await db.flush()
            
            created_articles.append((article, data))
            
            # Add stock tags
            for ticker in data["tickers"]:
                tag = NewsStockTag(
                    article_id=article.id,
                    ticker=ticker
                )
                db.add(tag)
            
            # Add sector tag
            sector_tag = NewsSectorTag(
                article_id=article.id,
                sector_name=data["sector"]
            )
            db.add(sector_tag)
            
            # Add sentiment analysis
            sentiment = NewsSentimentAnalysis(
                article_id=article.id,
                sentiment_label=data["sentiment"],
                confidence_score=abs(data["sentiment_score"]),
                sentiment_score=data["sentiment_score"],
                model_name="finbert",
                analyzed_at=datetime.utcnow()
            )
            db.add(sentiment)
            
            # Add reliability score
            reliability = NewsReliabilityScore(
                article_id=article.id,
                reliability_score=data["impact_score"],
                calculation_method="impact_model_v1",
                calculated_at=datetime.utcnow()
            )
            db.add(reliability)
        
        await db.commit()
        
        print(f"✅ Created {len(articles_data)} sample articles with tags, sentiment, and reliability scores!")
        
        # Verify
        from sqlalchemy import select, func
        result = await db.execute(select(func.count(NewsArticle.id)))
        count = result.scalar()
        print(f"Total articles in database: {count}")


if __name__ == "__main__":
    asyncio.run(populate_sample_data())
