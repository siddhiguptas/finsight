import httpx
from datetime import datetime, timedelta
from app.core.config import settings
from app.ingestion.base_client import BaseIngestionClient

class NewsAPIClient(BaseIngestionClient):
    def __init__(self):
        self.api_key = settings.newsapi_key
        self.base_url = "https://newsapi.org/v2/everything"

    async def fetch(self, tickers: list[str], days_back: int = 1):
        if not self.api_key:
            print("NewsAPI key not found in settings.")
            return []

        articles = []
        from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%dT%H:%M:%S')
        
        # Batch tickers to avoid too many requests
        # Broaden query: include quoted tickers and $TICKER variants
        raw_tickers = [t.strip().upper() for t in tickers[:10] if t and t.strip()]
        query_terms: list[str] = []
        for t in raw_tickers:
            if len(t) >= 2:
                query_terms.append(f"\"{t}\"")
                query_terms.append(f"${t}")
            else:
                # Single-letter tickers are ambiguous but still include quoted form
                query_terms.append(f"\"{t}\"")

        if not query_terms:
            query_terms = [f"\"{t}\"" for t in raw_tickers]

        query = " OR ".join(query_terms)
        
        async def _fetch_once(client: httpx.AsyncClient, label: str, from_dt: str) -> list[dict]:
            params = {
                "q": query,
                "from": from_dt,
                "sortBy": "publishedAt",
                "apiKey": self.api_key,
                "language": "en",
            }
            # Log the exact query and request params without leaking the API key
            safe_params = {k: v for k, v in params.items() if k != "apiKey"}
            print(f"NewsAPI request({label}): url={self.base_url} params={safe_params}")

            response = await client.get(
                self.base_url,
                params=params,
                timeout=10.0
            )
            print(f"NewsAPI response({label}): status_code={response.status_code}")
            response.raise_for_status()
            data = response.json()
            print(
                "NewsAPI response body summary: "
                f"status={data.get('status')} totalResults={data.get('totalResults')}"
            )

            if data.get("status") != "ok":
                return []

            items: list[dict] = []
            for art in data.get("articles", []):
                items.append({
                    "title": art["title"],
                    "url": art["url"],
                    "source_name": art["source"]["name"],
                    "published_at": art["publishedAt"],
                    "content": art["content"] or art["description"] or "",
                    "author": art.get("author"),
                    "image_url": art.get("urlToImage"),
                    "external_id": art["url"] # Use URL as external ID for NewsAPI
                })
            return items

        async with httpx.AsyncClient() as client:
            try:
                articles = await _fetch_once(client, "primary", from_date)

                if not articles:
                    retry_days_back = max(days_back, 3)
                    if retry_days_back != days_back:
                        retry_from = (datetime.utcnow() - timedelta(days=retry_days_back)).strftime('%Y-%m-%dT%H:%M:%S')
                        articles = await _fetch_once(client, "retry", retry_from)

                if not articles:
                    print("NewsAPI returned 0 articles. Falling back to RSS/Reddit.")
                    from app.ingestion.rss_scraper import RSSScraper
                    from app.ingestion.reddit_client import RedditClient

                    rss_articles = await RSSScraper().fetch(tickers)
                    reddit_articles = await RedditClient().fetch()
                    articles = rss_articles + reddit_articles

            except Exception as e:
                print(f"Error fetching from NewsAPI: {e}")
        
        return articles
