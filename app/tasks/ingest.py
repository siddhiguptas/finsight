import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from celery import shared_task
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.mongodb import mongo_db
from app.models.schemas import NewsArticle, TickerSectorMap, IngestionJobLog
from app.ingestion.newsapi_client import NewsAPIClient
from app.ingestion.rss_scraper import RSSScraper
from app.ingestion.reddit_client import RedditClient
from app.ingestion.alpha_vantage_client import AlphaVantageClient
from app.ingestion.sec_client import SECEdgarClient
from app.processing.deduplicator import compute_content_hash, is_duplicate
from app.core.redis import redis_client

async def save_article(article_data: dict):
    def parse_published_at(value: str) -> datetime:
        if not value:
            return datetime.utcnow()
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = parsedate_to_datetime(value)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                return datetime.utcnow()

    # Dedup
    content_hash = compute_content_hash(article_data["title"], article_data["content"])
    
    # Check if duplicate
    is_dup = await is_duplicate(content_hash, redis_client, None) # DB check handled by unique constraint or manual check
    
    async with AsyncSessionLocal() as session:
        # Check DB for duplicate URL or Hash
        stmt = select(NewsArticle).where((NewsArticle.external_id == article_data["external_id"]) | (NewsArticle.content_hash == content_hash))
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            return False

        # Store in MongoDB (Full body)
        mongo_res = await mongo_db.raw_articles.insert_one({
            "source": article_data["source_name"],
            "url": article_data["url"],
            "title": article_data["title"],
            "full_text": article_data["content"],
            "scraped_at": datetime.utcnow()
        })
        
        # Store in PostgreSQL
        new_article = NewsArticle(
            external_id=article_data["external_id"],
            source_name=article_data["source_name"],
            source_url=article_data["url"],
            title=article_data["title"],
            summary=article_data["content"][:500],
            full_text_ref=str(mongo_res.inserted_id),
            author=article_data.get("author"),
            published_at=parse_published_at(article_data.get("published_at")),
            content_hash=content_hash,
            image_url=article_data.get("image_url")
        )
        session.add(new_article)
        await session.commit()
        await session.refresh(new_article)
        
        # Cache hash in Redis
        await redis_client.setex(f"dedup:hash:{content_hash}", 172800, "1")
        
        # TRIGGER PROCESSING (Day 2 Pipeline)
        # If broker isn't available, skip async processing so ingestion still succeeds.
        try:
            from app.tasks.process import process_article
            process_article.delay(str(new_article.id))
        except Exception as e:
            print(f"Warning: could not enqueue processing task: {e}")
        
        return True


async def run_ingestion(job_name: str, fetch_coro):
    log = IngestionJobLog(job_name=job_name, started_at=datetime.utcnow(), status="RUNNING")
    async with AsyncSessionLocal() as session:
        session.add(log)
        await session.commit()
        await session.refresh(log)

    try:
        articles = await fetch_coro
        new_count = 0
        for art in articles:
            if await save_article(art):
                new_count += 1
        
        log.status = "SUCCESS"
        log.articles_fetched = len(articles)
        log.articles_new = new_count
        log.finished_at = datetime.utcnow()
    except Exception as e:
        log.status = "FAILED"
        log.error_message = str(e)
        log.finished_at = datetime.utcnow()
    
    async with AsyncSessionLocal() as session:
        session.add(log) # updates existing
        await session.merge(log)
        await session.commit()

@shared_task(name="app.tasks.ingest.fetch_newsapi")
def fetch_newsapi():
    async def _run():
        client = NewsAPIClient()
        # Get some tickers to search for
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(TickerSectorMap.ticker).limit(10))
            tickers = [r[0] for r in res]
        await run_ingestion("newsapi_poll", client.fetch(tickers))
    
    asyncio.run(_run())
    return {"status": "done"}

@shared_task(name="app.tasks.ingest.fetch_yahoo_rss")
def fetch_yahoo_rss():
    async def _run():
        client = RSSScraper()
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(TickerSectorMap.ticker).limit(10))
            tickers = [r[0] for r in res]
        await run_ingestion("yahoo_rss_poll", client.fetch(tickers))
    
    asyncio.run(_run())
    return {"status": "done"}

@shared_task(name="app.tasks.ingest.fetch_reddit")
def fetch_reddit():
    async def _run():
        client = RedditClient()
        await run_ingestion("reddit_poll", client.fetch())
    
    asyncio.run(_run())
    return {"status": "done"}

@shared_task(name="app.tasks.ingest.fetch_alpha_vantage")
def fetch_alpha_vantage():
    async def _run():
        client = AlphaVantageClient()
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(TickerSectorMap.ticker).limit(10))
            tickers = [r[0] for r in res]
        await run_ingestion("alpha_vantage_poll", client.fetch(tickers))
    
    asyncio.run(_run())
    return {"status": "done"}

@shared_task(name="app.tasks.ingest.fetch_sec_edgar")
def fetch_sec_edgar():
    async def _run():
        client = SECEdgarClient()
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(TickerSectorMap.ticker).limit(10))
            tickers = [r[0] for r in res]
        await run_ingestion("sec_edgar_poll", client.fetch(tickers))
    
    asyncio.run(_run())
    return {"status": "done"}
