import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from app.ingestion.newsapi_client import NewsAPIClient
from app.core.config import settings


class TestNewsAPIClient:
    """Test the NewsAPI client for news ingestion"""
    
    def setup_method(self):
        """Set up test client for each test method"""
        self.client = NewsAPIClient()
    
    def test_client_initialization(self):
        """Test that NewsAPIClient initializes correctly"""
        assert hasattr(self.client, 'api_key')
        assert hasattr(self.client, 'base_url')
        assert self.client.base_url == "https://newsapi.org/v2/everything"
    
    @pytest.mark.asyncio
    async def test_fetch_without_api_key(self):
        """Test fetch returns empty list when API key is not configured"""
        # Temporarily set API key to None
        original_key = self.client.api_key
        self.client.api_key = None
        
        try:
            result = await self.client.fetch(["AAPL", "MSFT"])
            assert result == []
        finally:
            self.client.api_key = original_key
    
    @pytest.mark.asyncio
    async def test_fetch_with_valid_tickers(self):
        """Test fetch with valid tickers"""
        # Mock successful API response
        mock_response = {
            "status": "ok",
            "totalResults": 2,
            "articles": [
                {
                    "title": "Apple Reports Record Earnings",
                    "url": "https://example.com/apple-earnings",
                    "source": {"name": "Reuters"},
                    "publishedAt": "2026-03-18T12:00:00Z",
                    "content": "Apple reports record earnings this quarter.",
                    "author": "John Doe",
                    "urlToImage": "https://example.com/image.jpg"
                },
                {
                    "title": "Microsoft Announces New AI Features",
                    "url": "https://example.com/microsoft-ai",
                    "source": {"name": "Bloomberg"},
                    "publishedAt": "2026-03-18T11:30:00Z",
                    "content": "Microsoft announces new AI features for Office.",
                    "author": "Jane Smith",
                    "urlToImage": None
                }
            ]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=AsyncMock(return_value=mock_response),
                raise_for_status=AsyncMock()
            )
            
            result = await self.client.fetch(["AAPL", "MSFT"])
            
            assert len(result) == 2
            assert result[0]["title"] == "Apple Reports Record Earnings"
            assert result[0]["source_name"] == "Reuters"
            assert result[0]["external_id"] == "https://example.com/apple-earnings"
            assert result[1]["title"] == "Microsoft Announces New AI Features"
    
    @pytest.mark.asyncio
    async def test_fetch_with_empty_tickers(self):
        """Test fetch with empty tickers list"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=AsyncMock(return_value={"status": "ok", "articles": []}),
                raise_for_status=AsyncMock()
            )
            
            result = await self.client.fetch([])
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_with_single_letter_tickers(self):
        """Test fetch handles single-letter tickers correctly"""
        mock_response = {
            "status": "ok",
            "totalResults": 1,
            "articles": [
                {
                    "title": "I-Bank Reports Results",
                    "url": "https://example.com/i-bank",
                    "source": {"name": "Financial Times"},
                    "publishedAt": "2026-03-18T10:00:00Z",
                    "content": "I-Bank reports quarterly results.",
                    "author": None,
                    "urlToImage": None
                }
            ]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=AsyncMock(return_value=mock_response),
                raise_for_status=AsyncMock()
            )
            
            result = await self.client.fetch(["I"])
            
            assert len(result) == 1
            assert result[0]["title"] == "I-Bank Reports Results"
    
    @pytest.mark.asyncio
    async def test_fetch_api_error_handling(self):
        """Test fetch handles API errors gracefully"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=401,
                raise_for_status=AsyncMock(side_effect=httpx.HTTPStatusError(
                    "Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
                ))
            )
            
            result = await self.client.fetch(["AAPL"])
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_network_error_handling(self):
        """Test fetch handles network errors gracefully"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Network error")
            
            result = await self.client.fetch(["AAPL"])
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_fallback_to_rss_when_no_articles(self):
        """Test fetch falls back to RSS/Reddit when NewsAPI returns no articles"""
        # Mock NewsAPI returning no articles
        mock_newsapi_response = {
            "status": "ok",
            "totalResults": 0,
            "articles": []
        }
        
        # Mock RSS response
        mock_rss_response = [
            {
                "title": "RSS News Article",
                "url": "https://rss.example.com/article",
                "source_name": "RSS Feed",
                "published_at": "2026-03-18T09:00:00Z",
                "content": "RSS content",
                "author": None,
                "image_url": None,
                "external_id": "https://rss.example.com/article"
            }
        ]
        
        # Mock Reddit response
        mock_reddit_response = [
            {
                "title": "Reddit Discussion",
                "url": "https://reddit.com/r/finance/comments/123",
                "source_name": "Reddit",
                "published_at": "2026-03-18T08:00:00Z",
                "content": "Reddit content",
                "author": "user123",
                "image_url": None,
                "external_id": "https://reddit.com/r/finance/comments/123"
            }
        ]
        
        with patch('httpx.AsyncClient.get') as mock_newsapi_get, \
             patch('app.ingestion.rss_scraper.RSSScraper.fetch') as mock_rss_fetch, \
             patch('app.ingestion.reddit_client.RedditClient.fetch') as mock_reddit_fetch:
            
            mock_newsapi_get.return_value = MagicMock(
                status_code=200,
                json=AsyncMock(return_value=mock_newsapi_response),
                raise_for_status=AsyncMock()
            )
            mock_rss_fetch.return_value = mock_rss_response
            mock_reddit_fetch.return_value = mock_reddit_response
            
            result = await self.client.fetch(["AAPL"])
            
            # Should return combined RSS and Reddit articles
            assert len(result) == 2
            assert any(article["source_name"] == "RSS Feed" for article in result)
            assert any(article["source_name"] == "Reddit" for article in result)
    
    @pytest.mark.asyncio
    async def test_fetch_query_construction(self):
        """Test that query is constructed correctly with tickers"""
        mock_response = {
            "status": "ok",
            "totalResults": 0,
            "articles": []
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=AsyncMock(return_value=mock_response),
                raise_for_status=AsyncMock()
            )
            
            # Mock RSS and Reddit to avoid actual calls
            with patch('app.ingestion.rss_scraper.RSSScraper.fetch', return_value=[]), \
                 patch('app.ingestion.reddit_client.RedditClient.fetch', return_value=[]):
                
                await self.client.fetch(["AAPL", "MSFT", "GOOGL"])
                
                # Verify the request was made with correct parameters
                mock_get.assert_called_once()
                call_args = mock_get.call_args
                params = call_args[1]['params']
                
                # Check that query contains ticker variations
                query = params['q']
                assert '"AAPL"' in query
                assert '"MSFT"' in query
                assert '"GOOGL"' in query
                assert '$AAPL' in query
                assert '$MSFT' in query
                assert '$GOOGL' in query
    
    @pytest.mark.asyncio
    async def test_fetch_date_range(self):
        """Test that fetch uses correct date range"""
        mock_response = {
            "status": "ok",
            "totalResults": 0,
            "articles": []
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=AsyncMock(return_value=mock_response),
                raise_for_status=AsyncMock()
            )
            
            # Mock RSS and Reddit to avoid actual calls
            with patch('app.ingestion.rss_scraper.RSSScraper.fetch', return_value=[]), \
                 patch('app.ingestion.reddit_client.RedditClient.fetch', return_value=[]):
                
                await self.client.fetch(["AAPL"], days_back=3)
                
                # Verify the request was made with correct date
                mock_get.assert_called_once()
                call_args = mock_get.call_args
                params = call_args[1]['params']
                
                # Check that from date is set correctly (3 days back)
                from_date = params['from']
                expected_date = (datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%S')
                assert from_date == expected_date