import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from app.ingestion.rss_scraper import RSSScraper


class TestRSSScraper:
    """Test the RSS scraper for news ingestion"""
    
    def setup_method(self):
        """Set up test client for each test method"""
        self.client = RSSScraper()
    
    def test_client_initialization(self):
        """Test that RSSScraper initializes correctly"""
        assert hasattr(self.client, 'fetch')
        assert callable(self.client.fetch)
    
    @pytest.mark.asyncio
    async def test_fetch_with_valid_tickers(self):
        """Test fetch with valid tickers"""
        # Mock Yahoo Finance RSS response
        mock_yahoo_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        <channel>
        <title>Yahoo Finance: AAPL</title>
        <item>
        <title>Apple Reports Record Earnings</title>
        <link>https://finance.yahoo.com/news/apple-reports-record-earnings-120000123.html</link>
        <pubDate>Wed, 18 Mar 2026 12:00:00 GMT</pubDate>
        <description>Apple reports record earnings this quarter.</description>
        <guid>https://finance.yahoo.com/news/apple-reports-record-earnings-120000123.html</guid>
        </item>
        </channel>
        </rss>"""
        
        # Mock Google News RSS response
        mock_google_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        <channel>
        <title>Google News: AAPL</title>
        <item>
        <title>Apple Stock Hits New High</title>
        <link>https://news.google.com/articles/CBMiYWh0dHBzOi8vd3d3LmJsb29tYmVyZy5jb20vbmV3cy9hcnRpY2xlcy9hcHBsZS1zdG9jay1oaXRzLW5ldy1oaWdoLWJhc2VkLW9uLWFuYWx5c3RzLW9wdGltaXNt0gEA?hl=en-US&gl=US&ceid=US%3Aen</link>
        <pubDate>Wed, 18 Mar 2026 11:30:00 GMT</pubDate>
        <description>Apple stock reaches new all-time high.</description>
        <guid>https://news.google.com/articles/CBMiYWh0dHBzOi8vd3d3LmJsb29tYmVyZy5jb20vbmV3cy9hcnRpY2xlcy9hcHBsZS1zdG9jay1oaXRzLW5ldy1oaWdoLWJhc2VkLW9uLWFuYWx5c3RzLW9wdGltaXNt0gEA?hl=en-US&gl=US&ceid=US%3Aen</guid>
        </item>
        </channel>
        </rss>"""
        
        with patch('httpx.AsyncClient.get') as mock_get:
            # Configure mock to return different responses for Yahoo and Google
            def side_effect(url, **kwargs):
                if 'yahoo' in url:
                    return MagicMock(
                        status_code=200,
                        text=mock_yahoo_rss,
                        raise_for_status=AsyncMock()
                    )
                else:  # Google News
                    return MagicMock(
                        status_code=200,
                        text=mock_google_rss,
                        raise_for_status=AsyncMock()
                    )
            
            mock_get.side_effect = side_effect
            
            result = await self.client.fetch(["AAPL"])
            
            assert len(result) == 2
            assert result[0]["title"] == "Apple Reports Record Earnings"
            assert result[0]["source_name"] == "Yahoo Finance"
            assert result[0]["external_id"] == "https://finance.yahoo.com/news/apple-reports-record-earnings-120000123.html"
            assert result[1]["title"] == "Apple Stock Hits New High"
            assert result[1]["source_name"] == "Google News"
    
    @pytest.mark.asyncio
    async def test_fetch_with_empty_tickers(self):
        """Test fetch with empty tickers list"""
        result = await self.client.fetch([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_with_multiple_tickers(self):
        """Test fetch with multiple tickers"""
        mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        <channel>
        <title>Test RSS</title>
        <item>
        <title>Test Article</title>
        <link>https://example.com/test</link>
        <pubDate>Wed, 18 Mar 2026 10:00:00 GMT</pubDate>
        <description>Test content</description>
        </item>
        </channel>
        </rss>"""
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                text=mock_rss,
                raise_for_status=AsyncMock()
            )
            
            result = await self.client.fetch(["AAPL", "MSFT"])
            
            # Should fetch from both Yahoo and Google for each ticker
            assert len(result) == 4  # 2 tickers * 2 sources each
            assert all(article["title"] == "Test Article" for article in result)
    
    @pytest.mark.asyncio
    async def test_fetch_handles_missing_fields(self):
        """Test fetch handles RSS items with missing fields"""
        mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        <channel>
        <title>Test RSS</title>
        <item>
        <title>Test Article</title>
        <link>https://example.com/test</link>
        <!-- Missing pubDate and description -->
        </item>
        </channel>
        </rss>"""
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                text=mock_rss,
                raise_for_status=AsyncMock()
            )
            
            result = await self.client.fetch(["AAPL"])
            
            assert len(result) == 1
            assert result[0]["title"] == "Test Article"
            assert result[0]["url"] == "https://example.com/test"
            assert result[0]["content"] == ""
            assert result[0]["published_at"] is not None  # Should have fallback datetime
    
    @pytest.mark.asyncio
    async def test_fetch_handles_network_errors(self):
        """Test fetch handles network errors gracefully"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Network error")
            
            result = await self.client.fetch(["AAPL"])
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_handles_http_errors(self):
        """Test fetch handles HTTP errors gracefully"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=404,
                raise_for_status=AsyncMock(side_effect=httpx.HTTPStatusError(
                    "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
                ))
            )
            
            result = await self.client.fetch(["AAPL"])
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_handles_invalid_rss(self):
        """Test fetch handles invalid RSS XML gracefully"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                text="Invalid XML content",
                raise_for_status=AsyncMock()
            )
            
            result = await self.client.fetch(["AAPL"])
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_uses_correct_urls(self):
        """Test fetch constructs correct RSS URLs"""
        mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        <channel>
        <title>Test RSS</title>
        <item>
        <title>Test Article</title>
        <link>https://example.com/test</link>
        </item>
        </channel>
        </rss>"""
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                text=mock_rss,
                raise_for_status=AsyncMock()
            )
            
            await self.client.fetch(["AAPL"])
            
            # Verify that both Yahoo and Google URLs were called
            assert mock_get.call_count == 2
            call_args_list = mock_get.call_args_list
            
            yahoo_url = call_args_list[0][0][0]
            google_url = call_args_list[1][0][0]
            
            assert "yahoo.com/rss/headline?s=AAPL" in yahoo_url
            assert "news.google.com/rss/search" in google_url
            assert "q=AAPL+stock+news" in google_url
    
    @pytest.mark.asyncio
    async def test_fetch_handles_timeout(self):
        """Test fetch handles request timeouts gracefully"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")
            
            result = await self.client.fetch(["AAPL"])
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_handles_empty_feed(self):
        """Test fetch handles RSS feeds with no items"""
        mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        <channel>
        <title>Empty RSS Feed</title>
        </channel>
        </rss>"""
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                text=mock_rss,
                raise_for_status=AsyncMock()
            )
            
            result = await self.client.fetch(["AAPL"])
            assert result == []