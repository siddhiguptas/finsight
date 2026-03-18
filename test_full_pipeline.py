#!/usr/bin/env python3
import asyncio
from app.tasks.ingest import run_ingestion
from app.ingestion.rss_scraper import RSSScraper
from app.tasks.process import process_article
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.schemas import TickerSectorMap

async def test_pipeline():
    # Get tickers
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(TickerSectorMap.ticker).limit(5))
        tickers = [r[0] for r in res]
    
    client = RSSScraper()
    await run_ingestion('test_rss', client.fetch(tickers[:3]))
    
    # Wait a bit, then check processing
    await asyncio.sleep(5)
    print('Ingestion complete. Processing should be enqueued via Celery.')

asyncio.run(test_pipeline())

