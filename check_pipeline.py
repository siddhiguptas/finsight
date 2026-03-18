#!/usr/bin/env python3
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.schemas import NewsArticle, IngestionJobLog, NewsStockTag, NewsSentimentAnalysis, NewsSectorTag

async def check_db():
    async with AsyncSessionLocal() as session:
        cutoff = datetime.utcnow() - timedelta(hours=2)
        
        # Recent jobs
        jobs = await session.execute(select(IngestionJobLog).where(IngestionJobLog.started_at > cutoff))
        recent_jobs = jobs.scalars().all()
        
        # Recent articles
        articles = await session.execute(select(NewsArticle.id).where(NewsArticle.created_at > cutoff))
        recent_articles = articles.scalars().all()
        
        # Tags and sentiment
        tags = await session.execute(select(NewsStockTag).where(NewsStockTag.created_at > cutoff))
        recent_tags = tags.scalars().all()
        
        sent = await session.execute(select(NewsSentimentAnalysis).where(NewsSentimentAnalysis.created_at > cutoff))
        recent_sent = sent.scalars().all()
        
        sectors = await session.execute(select(NewsSectorTag).where(NewsSectorTag.created_at > cutoff))
        recent_sectors = sectors.scalars().all()
        
        print(f'Recent Jobs ({len(recent_jobs)}): {[j.job_name for j in recent_jobs]}')
        print(f'Recent Articles ({len(recent_articles)})')
        print(f'Recent Stock Tags ({len(recent_tags)})')
        print(f'Recent Sentiment Analyses ({len(recent_sent)})')
        print(f'Recent Sector Tags ({len(recent_sectors)})')

if __name__ == '__main__':
    asyncio.run(check_db())

