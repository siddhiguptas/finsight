import httpx
from datetime import datetime, timedelta
from app.ingestion.base_client import BaseIngestionClient

class SECEdgarClient(BaseIngestionClient):
    def __init__(self):
        self.base_url = "https://efts.sec.gov/LATEST/search-index"
        self.forms = ["8-K", "10-K", "10-Q", "DEF 14A"]

    async def fetch(self, tickers: list[str] = None, days_back: int = 7):
        articles = []
        from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "dateRange": "custom",
                    "startdt": from_date,
                    "enddt": datetime.utcnow().strftime('%Y-%m-%d'),
                    "forms": self.forms[0],
                    "page": 1,
                    "length": 40
                }

                response = await client.get(
                    self.base_url,
                    params=params,
                    timeout=20.0,
                    headers={"User-Agent": "FinSight/1.0 (research@finsight.com)"}
                )

                if response.status_code != 200:
                    return articles

                data = response.json()

                for hit in data.get("hits", {}).get("hits", []):
                    source = hit.get("_source", {})
                    display_names = source.get("displayNames", [])

                    title = display_names[0] if display_names else "SEC Filing"
                    form_type = source.get("formType", "")
                    cik = source.get("cikStr", "")
                    company_name = source.get("entityName", "")

                    filing_date = source.get("filedDate", "")
                    acceptance_datetime = source.get("acceptanceDatetime", "")

                    filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{source.get('accessionNumber', '')}/index.json"

                    article = {
                        "title": f"{company_name} {form_type} Filing",
                        "url": filing_url,
                        "source_name": "SEC EDGAR",
                        "published_at": filing_date or acceptance_datetime,
                        "content": f"{form_type} filing by {company_name}. This is an official regulatory filing with the Securities and Exchange Commission.",
                        "author": company_name,
                        "image_url": None,
                        "external_id": f"sec_{cik}_{source.get('accessionNumber', '')}",
                        "ticker": company_name,
                        "form_type": form_type
                    }
                    articles.append(article)

            except Exception as e:
                print(f"Error fetching from SEC EDGAR: {e}")

        return articles
