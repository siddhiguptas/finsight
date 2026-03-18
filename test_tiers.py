#!/usr/bin/env python3
"""Test news feed with different tiers."""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def test_tiers():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("="*60)
        print("Testing News Feed with Different Tiers")
        print("="*60)
        
        # Get token
        r = await client.post(
            f"{BASE_URL}/api/v1/auth/token",
            json={"user_id": "550e8400-e29b-41d4-a716-446655440000", "role": "student"}
        )
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 1: General tier (default)
        print("\n1. GET /api/v1/news/feed?tier=general")
        r = await client.get(
            f"{BASE_URL}/api/v1/news/feed?tier=general&limit=5",
            headers=headers
        )
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Count: {data.get('count', 0)}")
            for art in data.get('articles', [])[:2]:
                print(f"   - {art.get('title', 'N/A')[:50]}...")
        
        # Test 2: Market tier
        print("\n2. GET /api/v1/news/feed?tier=market")
        r = await client.get(
            f"{BASE_URL}/api/v1/news/feed?tier=market&limit=5",
            headers=headers
        )
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Count: {data.get('count', 0)}")
        
        # Test 3: Portfolio tier with tickers
        print("\n3. GET /api/v1/news/feed?tier=portfolio&tickers=AAPL,MSFT")
        r = await client.get(
            f"{BASE_URL}/api/v1/news/feed?tier=portfolio&tickers=AAPL,MSFT&limit=5",
            headers=headers
        )
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Count: {data.get('count', 0)}")
            for art in data.get('articles', [])[:2]:
                print(f"   - {art.get('title', 'N/A')[:50]}...")
                print(f"     Tickers: {art.get('tickers', [])}")
        
        # Test 4: Portfolio tier with user_id (watchlist)
        print("\n4. GET /api/v1/news/feed?tier=portfolio&user_id=<uuid>")
        r = await client.get(
            f"{BASE_URL}/api/v1/news/feed?tier=portfolio&user_id=550e8400-e29b-41d4-a716-446655440000&limit=5",
            headers=headers
        )
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Count: {data.get('count', 0)}")
        
        # Test 5: Sector tier
        print("\n5. GET /api/v1/news/feed?tier=sector&sector=Technology")
        r = await client.get(
            f"{BASE_URL}/api/v1/news/feed?tier=sector&sector=Technology&limit=5",
            headers=headers
        )
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Count: {data.get('count', 0)}")
            for art in data.get('articles', [])[:2]:
                print(f"   - {art.get('title', 'N/A')[:50]}...")
        
        # Test 6: With filters - impact_level
        print("\n6. GET /api/v1/news/feed?impact_level=HIGH")
        r = await client.get(
            f"{BASE_URL}/api/v1/news/feed?impact_level=HIGH&limit=5",
            headers=headers
        )
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Count: {data.get('count', 0)}")
        
        # Test 7: With filters - sentiment
        print("\n7. GET /api/v1/news/feed?sentiment=POSITIVE")
        r = await client.get(
            f"{BASE_URL}/api/v1/news/feed?sentiment=POSITIVE&limit=5",
            headers=headers
        )
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Count: {data.get('count', 0)}")
        
        # Test 8: Combined filters
        print("\n8. GET /api/v1/news/feed?tier=portfolio&tickers=AAPL&impact_level=HIGH&sentiment=POSITIVE")
        r = await client.get(
            f"{BASE_URL}/api/v1/news/feed?tier=portfolio&tickers=AAPL&impact_level=HIGH&sentiment=POSITIVE&limit=5",
            headers=headers
        )
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Count: {data.get('count', 0)}")
        
        print("\n" + "="*60)
        print("All tier tests complete!")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(test_tiers())
