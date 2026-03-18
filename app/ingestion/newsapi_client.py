import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from app.core.config import settings
from app.ingestion.base_client import BaseIngestionClient

logger = logging.getLogger(__name__)

class NewsAPIClient(BaseIngestionClient):
    def __init__(self):
        self.api_key = settings.newsapi_key
        self.base_url = "https://newsapi.org/v2/everything"
        self.max_tickers = 10
        self.request_timeout = 10.0
        self.max_retries = 2

    async def fetch(self, tickers: List[str], days_back: int = 1) -> List[Dict[str, Any]]:
        """
        Fetch news articles from NewsAPI with fallback to RSS/Reddit.
        
        Args:
            tickers: List of stock tickers to search for
            days_back: Number of days to look back for articles
            
        Returns:
            List of article dictionaries
        """
        if not self.api_key:
            logger.warning("NewsAPI key not found in settings. Skipping NewsAPI fetch.")
            return []

        if not tickers:
            logger.warning("No tickers provided for NewsAPI fetch.")
            return []

        articles = []
        from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%dT%H:%M:%S')
        
        # Process tickers safely
        processed_tickers = self._process_tickers(tickers)
        if not processed_tickers:
            logger.warning("No valid tickers found after processing.")
            return []

        query = self._build_query(processed_tickers)
        logger.info(f"NewsAPI query: {query}")
        
        async with httpx.AsyncClient() as client:
            try:
                # Primary fetch attempt
                articles = await self._fetch_once(client, "primary", query, from_date)
                
                # Retry with extended date range if no articles found
                if not articles and days_back < 7:
                    retry_days_back = min(days_back * 2, 7)
                    retry_from = (datetime.utcnow() - timedelta(days=retry_days_back)).strftime('%Y-%m-%dT%H:%M:%S')
                    logger.info(f"No articles found, retrying with extended date range: {retry_days_back} days")
                    articles = await self._fetch_once(client, "retry", query, retry_from)

                # Fallback to RSS/Reddit if still no articles
                if not articles:
                    logger.info("NewsAPI returned 0 articles. Falling back to RSS/Reddit.")
                    articles = await self._fetch_fallback_sources(processed_tickers)

            except Exception as e:
                logger.error(f"Error fetching from NewsAPI: {e}", exc_info=True)
                # Still try fallback sources on error
                articles = await self._fetch_fallback_sources(processed_tickers)
        
        logger.info(f"NewsAPI fetch completed. Found {len(articles)} articles.")
        return articles

    def _process_tickers(self, tickers: List[str]) -> List[str]:
        """Process and validate tickers for querying."""
        processed = []
        for ticker in tickers[:self.max_tickers]:
            if not ticker or not ticker.strip():
                continue
            ticker = ticker.strip().upper()
            if len(ticker) >= 1:  # Allow single-letter tickers but log them
                if len(ticker) == 1:
                    logger.warning(f"Single-letter ticker detected: {ticker}. May produce ambiguous results.")
                processed.append(ticker)
        return processed

    def _build_query(self, tickers: List[str]) -> str:
        """Build search query with ticker variations."""
        query_terms = []
        for ticker in tickers:
            if len(ticker) >= 2:
                query_terms.extend([f"\"{ticker}\"", f"${ticker}"])
            else:
                query_terms.append(f"\"{ticker}\"")
        
        return " OR ".join(query_terms)

    async def _fetch_once(self, client: httpx.AsyncClient, label: str, query: str, from_date: str) -> List[Dict[str, Any]]:
        """Fetch articles from NewsAPI once."""
        params = {
            "q": query,
            "from": from_date,
            "sortBy": "publishedAt",
            "apiKey": self.api_key,
            "language": "en",
            "pageSize": 100,  # Max allowed by NewsAPI
        }
        
        # Log request safely (exclude API key)
        safe_params = {k: v for k, v in params.items() if k != "apiKey"}
        logger.debug(f"NewsAPI request({label}): url={self.base_url} params={safe_params}")

        try:
            response = await client.get(
                self.base_url,
                params=params,
                timeout=self.request_timeout
            )
            
            logger.debug(f"NewsAPI response({label}): status_code={response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            logger.debug(
                f"NewsAPI response summary: status={data.get('status')} totalResults={data.get('totalResults')}"
            )

            if data.get("status") != "ok":
                logger.warning(f"NewsAPI returned non-ok status: {data.get('status')}")
                return []

            articles = []
            for article in data.get("articles", []):
                processed_article = self._process_article(article)
                if processed_article:
                    articles.append(processed_article)
            
            logger.info(f"NewsAPI {label} fetch: {len(articles)} valid articles processed")
            return articles

        except httpx.HTTPStatusError as e:
            logger.error(f"NewsAPI HTTP error ({label}): {e.response.status_code} - {e.response.text}")
            return []
        except httpx.TimeoutException:
            logger.error(f"NewsAPI request timeout ({label})")
            return []
        except httpx.RequestError as e:
            logger.error(f"NewsAPI request error ({label}): {e}")
            return []
        except Exception as e:
            logger.error(f"NewsAPI unexpected error ({label}): {e}", exc_info=True)
            return []

    def _process_article(self, article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single article and extract required fields."""
        try:
            # Validate required fields
            title = article.get("title")
            url = article.get("url")
            source_name = article.get("source", {}).get("name")
            
            if not all([title, url, source_name]):
                logger.debug(f"Skipping article with missing required fields: {title}, {url}, {source_name}")
                return None

            # Extract content (try content first, then description)
            content = article.get("content") or article.get("description") or ""
            
            processed = {
                "title": title,
                "url": url,
                "source_name": source_name,
                "published_at": article.get("publishedAt", ""),
                "content": content,
                "author": article.get("author"),
                "image_url": article.get("urlToImage"),
                "external_id": url  # Use URL as external ID for NewsAPI
            }
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing article: {e}", exc_info=True)
            return None

    async def _fetch_fallback_sources(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """Fetch articles from fallback sources (RSS/Reddit)."""
        fallback_articles = []
        
        try:
            from app.ingestion.rss_scraper import RSSScraper
            from app.ingestion.reddit_client import RedditClient

            # Fetch from RSS
            rss_scraper = RSSScraper()
            rss_articles = await rss_scraper.fetch(tickers)
            fallback_articles.extend(rss_articles)
            logger.info(f"RSS fallback: {len(rss_articles)} articles")

            # Fetch from Reddit
            reddit_client = RedditClient()
            reddit_articles = await reddit_client.fetch()
            fallback_articles.extend(reddit_articles)
            logger.info(f"Reddit fallback: {len(reddit_articles)} articles")

        except Exception as e:
            logger.error(f"Error fetching fallback sources: {e}", exc_info=True)
        
        return fallback_articles
