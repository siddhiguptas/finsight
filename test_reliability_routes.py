#!/usr/bin/env python3
"""Test reliability routes."""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def test_reliability():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("="*60)
        print("Testing Reliability API Routes")
        print("="*60)
        
        # Get token
        r = await client.post(
            f"{BASE_URL}/api/v1/auth/token",
            json={"user_id": "550e8400-e29b-41d4-a716-446655440000", "role": "student"}
        )
        if r.status_code != 200:
            print(f"Token error: {r.status_code} - {r.text}")
            return
            
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 1: Source reliability list
        print("\n1. GET /api/v1/reliability/sources")
        r = await client.get(f"{BASE_URL}/api/v1/reliability/sources", headers=headers)
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Sources found: {len(data)}")
            for s in data:
                print(f"   - {s['source_name']}: accuracy_24h={s.get('accuracy_24h')}, total={s.get('total_articles')}")
        
        # Test 2: Source detail
        print("\n2. GET /api/v1/reliability/source/newsapi")
        r = await client.get(f"{BASE_URL}/api/v1/reliability/source/newsapi", headers=headers)
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Source: {data.get('source_name')}")
            print(f"   Reliability tier: {data.get('reliability_tier')}")
            print(f"   Accuracy 24h: {data.get('accuracy_24h')}")
        
        # Test 3: Source not found
        print("\n3. GET /api/v1/reliability/source/invalid (404 expected)")
        r = await client.get(f"{BASE_URL}/api/v1/reliability/source/invalid", headers=headers)
        print(f"   Status: {r.status_code}")
        
        # Test 4: Ticker reliability (if data exists)
        print("\n4. GET /api/v1/reliability/ticker/AAPL")
        r = await client.get(f"{BASE_URL}/api/v1/reliability/ticker/AAPL", headers=headers)
        print(f"   Status: {r.status_code}")
        if r.status_code == 404:
            print("   (No reliability data yet - needs nightly backtest)")
        
        print("\n" + "="*60)
        print("Reliability tests complete!")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(test_reliability())
