#!/usr/bin/env python3
import httpx
import asyncio

BASE_URL = "http://localhost:8000"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"

async def test_routes():
    token = None
    headers = {}
    valid_article_id = None  # Will be set from portfolio feed test
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 60)
        print("Testing FinSight API Routes")
        print("=" * 60)
        
        print("\n1. Testing Health
