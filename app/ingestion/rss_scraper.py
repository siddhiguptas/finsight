import feedparser
import httpx
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.ingestion.base_client import BaseIngestionClient

logger = logging.getLogger(__name__)

class RSSScraper(BaseIngestionClient):
    def __init__(self):
        self.request_timeout = 15.0
        self.max_tickers = 10
        self.yahoo_base_url = "https://finance.yahoo.com/rss/headline?s={}"
        self.google_base_url = "https://news.google.com/rss/search?q={ticker}+stock+news&hl=en-US&gl=US&ceid=US:en"

    async def fetch(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch articles from RSS feeds (Yahoo Finance and Google News).
        
        Args:
            tickers: List of stock tickers to search for
            
        Returns:
            List of article dictionaries
        """
        if not tickers:
            logger.warning("No tickers provided for RSS fetch.")
            return []

        # Process and validate tickers
        processed_tickers = self._process_tickers(tickers)
        if not processed_tickers:
            logger.warning("No valid tickers found after processing.")
            return []

        articles = []
        
        # Fetch from each ticker and source combination
        for ticker in processed_tickers:
            ticker_articles = await self._fetch_for_ticker(ticker)
            articles.extend(ticker_articles)
        
        logger.info(f"RSS fetch completed. Found {len(articles)} articles from {len(processed_tickers)} tickers.")
        return articles

    def _process_tickers(self, tickers: List[str]) -> List[str]:
        """Process and validate tickers."""
        processed = []
        for ticker in tickers[:self.max_tickers]:
            if not ticker or not ticker.strip():
                continue
            ticker = ticker.strip().upper()
            if len(ticker) >= 1:
                processed.append(ticker)
        return processed

    async def _fetch_for_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetch articles for a specific ticker from all RSS sources."""
        ticker_articles = []
        
        # Define RSS sources
        sources = [
            {
                "name": "Yahoo Finance",
                "url": self.yahoo_base_url.format(ticker),
                "priority": 1
            },
            {
                "name": "Google News",
                "url": self.google_base_url.format(ticker=ticker),
                "priority": 2
            }
        ]
        
        for source in sources:
            try:
                source_articles = await self._fetch_from_source(source["name"], source["url"])
                ticker_articles.extend(source_articles)
                logger.debug(f"RSS {source['name']} for {ticker}: {len(source_articles)} articles")
                
            except Exception as e:
                logger.error(f"Error fetching RSS from {source['name']} for {ticker}: {e}", exc_info=True)
        
        return ticker_articles

    async def _fetch_from_source(self, source_name: str, url: str) -> List[Dict[str, Any]]:
        """Fetch articles from a specific RSS source."""
        articles = []
        
        try:
            logger.debug(f"Fetching RSS from {source_name}: {url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=self.request_timeout)
                response.raise_for_status()
                
                # Parse RSS feed
                feed = feedparser.parse(response.text)
                
                if not feed.entries:
                    logger.debug(f"No entries found in RSS feed: {source_name}")
                    return articles

                for entry in feed.entries:
                    processed_entry = self._process_rss_entry(entry, source_name)
                    if processed_entry:
                        articles.append(processed_entry)
                
                logger.info(f"RSS {source_name}: processed {len(articles)} articles")
                return articles

        except httpx.HTTPStatusError as e:
            logger.error(f"RSS HTTP error from {source_name}: {e.response.status_code}")
            return []
        except httpx.TimeoutException:
            logger.error(f"RSS request timeout from {source_name}")
            return []
        except httpx.RequestError as e:
            logger.error(f"RSS request error from {source_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"RSS unexpected error from {source_name}: {e}", exc_info=True)
            return []

    def _process_rss_entry(self, entry: Any, source_name: str) -> Optional[Dict[str, Any]]:
        """Process a single RSS entry and extract required fields."""
        try:
            # Extract required fields
            title = getattr(entry, 'title', '').strip()
            link = getattr(entry, 'link', '').strip()
            
            if not title or not link:
                logger.debug(f"Skipping RSS entry with missing title or link: {title}")
                return None

            # Extract optional fields with fallbacks
            published_at = self._extract_date(entry)
            content = self._extract_content(entry)
            external_id = getattr(entry, 'id', link)  # Use link as fallback for external_id

            processed = {
                "title": title,
                "url": link,
                "source_name": source_name,
                "published_at": published_at,
                "content": content,
                "author": getattr(entry, 'author', None),
                "image_url": getattr(entry, 'image', None),
                "external_id": external_id
            }
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing RSS entry: {e}", exc_info=True)
            return None

    def _extract_date(self, entry: Any) -> str:
        """Extract and normalize publication date."""
        # Try multiple date fields in order of preference
        date_fields = ['published_parsed', 'updated_parsed', 'published', 'updated']
        
        for field in date_fields:
            date_value = getattr(entry, field, None)
            if date_value:
                try:
                    if isinstance(date_value, tuple):
                        # feedparser parsed date tuple
                        dt = datetime(*date_value[:6])
                        return dt.isoformat()
                    else:
                        # String date
                        return str(date_value)
                except (ValueError, TypeError):
                    continue
        
        # Fallback to current time
        logger.debug("No valid date found in RSS entry, using current time")
        return datetime.utcnow().isoformat()

    def _extract_content(self, entry: Any) -> str:
        """Extract content with fallbacks."""
        content_fields = ['summary', 'description', 'content']
        
        for field in content_fields:
            content = getattr(entry, field, '')
            if content and content.strip():
                # Clean up content (remove HTML tags if present)
                return self._clean_content(str(content))
        
        return ""

    def _clean_content(self, content: str) -> str:
        """Clean HTML content and normalize."""
        import re
        
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', content)
        
        # Normalize whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        return clean

