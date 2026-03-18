import asyncio
import os

from dotenv import load_dotenv

# Load env before importing app modules that initialize settings/engines
load_dotenv()

from app.tasks.ingest import fetch_newsapi
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.schemas import NewsArticle

async def test_ingest():
    print("Testing NewsAPI Ingestion...")
    # This calls the celery task function directly
    # We call the underlying async function logic
    from app.ingestion.newsapi_client import NewsAPIClient
    from app.tasks.ingest import run_ingestion
    from app.models.schemas import TickerSectorMap
    
    async with AsyncSessionLocal() as session:
        # Just pick 10 tickers to be sure we get some hits
        res = await session.execute(select(TickerSectorMap.ticker).limit(10))
        tickers = [r[0] for r in res]
        print(f"Fetching for: {tickers}")

        
    client = NewsAPIClient()
    # Manual run of the core logic
    articles = await client.fetch(tickers)
    print(f"Fetched {len(articles)} articles.")
    
    from app.tasks.ingest import save_article
    new_count = 0
    for art in articles[:5]: # just test first 5
        if await save_article(art):
            new_count += 1
            print(f"Saved: {art['title'][:50]}...")
    
    print(f"Total New Saved: {new_count}")

if __name__ == "__main__":
    asyncio.run(test_ingest())
