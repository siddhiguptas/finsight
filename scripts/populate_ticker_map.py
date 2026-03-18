import pandas as pd
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.schemas import TickerSectorMap

async def populate_ticker_map():
    print("Fetching S&P 500 tickers and sectors from Wikipedia...")
    try:
        # Scrape S&P 500 table from Wikipedia
        # Scrape S&P 500 table from Wikipedia with User-Agent
        import urllib.request
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            tables = pd.read_html(response)
        df = tables[0]

        
        # We need Ticker, Security (Company Name), GICS Sector
        # Columns: 'Symbol', 'Security', 'GICS Sector', 'GICS Sub-Industry', 'Headquarters Location', 'Date added', 'CIK', 'Founded'
        df = df[['Symbol', 'Security', 'GICS Sector', 'GICS Sub-Industry']]
        
        async with AsyncSessionLocal() as session:
            for _, row in df.iterrows():
                ticker = row['Symbol'].replace('.', '-') # normalize for Yahoo/APIs
                
                # Check if exists
                stmt = select(TickerSectorMap).where(TickerSectorMap.ticker == ticker)
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    continue
                
                new_ticker = TickerSectorMap(
                    ticker=ticker,
                    company_name=row['Security'],
                    sector=row['GICS Sector'],
                    industry=row['GICS Sub-Industry']
                )
                session.add(new_ticker)
            
            await session.commit()
            print(f"Successfully populated {len(df)} tickers.")
            
    except Exception as e:
        print(f"Error populating ticker map: {e}")

if __name__ == "__main__":
    asyncio.run(populate_ticker_map())

