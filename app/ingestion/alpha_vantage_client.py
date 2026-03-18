import httpx
from datetime import datetime, timedelta
from app.core.config import settings
from app.ingestion.base_client import BaseIngestionClient

class AlphaVantageClient(BaseIngestionClient):
    def __init__(self):
        self.api_key = settings.alpha_vantage_key
        self.base_url = "https://www.alphavantage.co/query"

    async def fetch(self, tickers: list[str], days_back: int = 1):
        if not self.api_key:
            print("Alpha Vantage key not found in settings.")
            return []

        articles = []
        from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        async with httpx.AsyncClient() as client:
            for ticker in tickers[:10]:
                try:
                    params = {
                        "function": "NEWS_SENTIMENT",
                        "tickers": ticker,
                        "time_from": from_date.replace('-', ''),
                        "sort": "LATEST",
                        "limit": 50,
                        "apikey": self.api_key
                    }

                    response = await client.get(
                        self.base_url,
                        params=params,
                        timeout=15.0
                    )

                    if response.status_code != 200:
                        continue

                    data = response.json()

                    if "feed" not in data:
                        continue

                    for item in data.get("feed", []):
                        article = {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "source_name": item.get("source", ""),
                            "published_at": item.get("time_published", ""),
                            "content": item.get("summary", ""),
                            "author": item.get("authors", [""])[0] if item.get("authors") else None,
                            "image_url": item.get("banner_image"),
                            "external_id": item.get("url", ""),
                            "ticker": ticker,
                            "sentiment": item.get("overall_sentiment_label", "NEUTRAL"),
                            "sentiment_score": item.get("overall_sentiment_score", 0)
                        }
                        articles.append(article)

                except Exception as e:
                    print(f"Error fetching from Alpha Vantage for {ticker}: {e}")
                    continue

        return articles
