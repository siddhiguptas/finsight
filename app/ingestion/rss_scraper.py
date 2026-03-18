import feedparser
import httpx
import asyncio
from datetime import datetime
from app.ingestion.base_client import BaseIngestionClient

class RSSScraper(BaseIngestionClient):
    async def fetch(self, tickers: list[str]):
        articles = []
        
        # Fetch for each ticker
        for ticker in tickers:
            # Yahoo Finance RSS
            yahoo_url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
            # Google News RSS
            google_url = f"https://news.google.com/rss/search?q={ticker}+stock+news&hl=en-US&gl=US&ceid=US:en"
            
            for url in [yahoo_url, google_url]:
                try:
                    # feedparser is synchronous, we can run in thread or just use it as is if it's not a bottleneck
                    # but it's better to fetch raw XML asynchronously and then parse
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(url, timeout=10.0)
                        resp.raise_for_status()
                        feed = feedparser.parse(resp.text)
                        
                        for entry in feed.entries:
                            articles.append({
                                "title": entry.title,
                                "url": entry.link,
                                "source_name": "Yahoo Finance" if "yahoo" in url else "Google News",
                                "published_at": entry.get("published") or entry.get("updated") or datetime.utcnow().isoformat(),
                                "content": entry.get("summary") or entry.get("description") or "",
                                "external_id": entry.id if hasattr(entry, 'id') else entry.link
                            })
                except Exception as e:
                    print(f"Error scraping RSS {url}: {e}")
                    
        return articles

