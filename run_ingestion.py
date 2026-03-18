#!/usr/bin/env python3
"""
Direct ingestion script - run this to fetch and save news articles to the database.
No Celery required - runs directly.

Usage:
    python run_ingestion.py              # Fetch from all sources
    python run_ingestion.py --source newsapi   # Fetch from specific source
    python run_ingestion.py --help
"""
import asyncio
import argparse
from datetime import datetime, timezone

from app.core.database import AsyncSessionLocal
from app.models.schemas import TickerSectorMap
from app.ingestion.newsapi_client import NewsAPIClient
from app.ingestion.rss_scraper import RSSScraper
from app.ingestion.reddit_client import RedditClient
from app.ingestion.alpha_vantage_client import AlphaVantageClient
from app.ingestion.sec_client import SECEdgarClient
from app.tasks.ingest import save_article


async def get_tickers(session):
    """Get list of tickers from database."""
    from sqlalchemy import select
    result = await session.execute(select(TickerSectorMap.ticker).limit(20))
    return [r[0] for r in result.all()]


async def run_source(source_name: str, client, tickers: list = None):
    """Run ingestion for a specific source."""
    print(f"\n{'='*60}")
    print(f"Fetching from {source_name}...")
    print(f"{'='*60}")
    
    try:
        if tickers:
            articles = await client.fetch(tickers)
        else:
            articles = await client.fetch()
        
        print(f"Fetched {len(articles)} articles")
        
        saved_count = 0
        for article in articles:
            try:
                result = await save_article(article)
                if result:
                    saved_count += 1
            except Exception as e:
                print(f"Error saving article: {e}")
        
        print(f"Saved {saved_count} new articles to database")
        return saved_count
        
    except Exception as e:
        print(f"Error fetching from {source_name}: {e}")
        return 0


async def main(source: str = "all"):
    """Main entry point."""
    print(f"Starting direct ingestion for source: {source}")
    
    async with AsyncSessionLocal() as session:
        tickers = await get_tickers(session)
        print(f"Found {len(tickers)} tickers: {tickers}")
    
    if not tickers:
        # Use default tickers if none in DB
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "WMT"]
        print(f"Using default tickers: {tickers}")
    
    total_saved = 0
    
    if source in ("all", "newsapi"):
        client = NewsAPIClient()
        total_saved += await run_source("NewsAPI", client, tickers)
    
    if source in ("all", "rss"):
        client = RSSScraper()
        total_saved += await run_source("RSS Feeds", client, tickers)
    
    if source in ("all", "reddit"):
        client = RedditClient()
        total_saved += await run_source("Reddit", client)
    
    if source in ("all", "alphavantage"):
        client = AlphaVantageClient()
        total_saved += await run_source("Alpha Vantage", client, tickers)
    
    if source in ("all", "sec"):
        client = SECEdgarClient()
        total_saved += await run_source("SEC EDGAR", client, tickers)
    
    print(f"\n{'='*60}")
    print(f"INGESTION COMPLETE")
    print(f"Total new articles saved: {total_saved}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run news ingestion directly")
    parser.add_argument(
        "--source", 
        default="all",
        choices=["all", "newsapi", "rss", "reddit", "alphavantage", "sec"],
        help="Source to fetch from (default: all)"
    )
    args = parser.parse_args()
    
    asyncio.run(main(args.source))
