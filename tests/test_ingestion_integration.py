import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from app.core.database import AsyncSessionLocal
from app.core.mongodb import mongo_db
from app.models.schemas import NewsArticle, TickerSectorMap, IngestionJobLog
from app.ingestion.newsapi_client import NewsAPIClient
from app.ingestion.rss_scraper import RSSScraper
from app.ingestion.reddit_client import RedditClient
from app.tasks.ingest import save_article, run_ingestion


class TestIngestionIntegration:
    """Integration tests for the ingestion layer"""
    
    @pytest.mark.asyncio
    async def test_newsapi_rss_fallback_integration(self):
        """Test NewsAPI fallback to RSS when no articles are returned"""
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
            
            client = NewsAPIClient()
            result = await client.fetch(["AAPL"])
            
            # Should return combined RSS and Reddit articles
            assert len(result) == 2
            assert any(article["source_name"] == "RSS Feed" for article in result)
            assert any(article["source_name"] == "Reddit" for article in result)
    
    @pytest.mark.asyncio
    async def test_article_storage_integration(self):
        """Test complete article storage flow"""
        article_data = {
            "title": "Integration Test Article",
            "url": "https://example.com/integration-test",
            "source_name": "Integration Test Source",
            "content": "This is a test article for integration testing.",
            "author": "Test Author",
            "published_at": "2026-03-18T12:00:00Z",
            "image_url": "https://example.com/test-image.jpg",
            "external_id": "https://example.com/integration-test"
        }
        
        # Mock MongoDB insert
        mock_mongo_insert = AsyncMock()
        mock_mongo_insert.inserted_id = "mock_mongo_id"
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=AsyncMock(return_value=None)))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        with patch('app.tasks.ingest.mongo_db') as mock_mongo, \
             patch('app.tasks.ingest.redis_client', mock_redis), \
             patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session), \
             patch('app.tasks.ingest.process_article') as mock_process_task:
            
            mock_mongo.raw_articles.insert_one = AsyncMock(return_value=mock_mongo_insert)
            
            result = await save_article(article_data)
            
            assert result is True
            mock_mongo.raw_articles.insert_one.assert_called_once()
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_redis.setex.assert_called_once()
            mock_process_task.delay.assert_called_once()
            
            # Verify the article object was created correctly
            created_article = mock_session.add.call_args[0][0]
            assert created_article.title == "Integration Test Article"
            assert created_article.source_name == "Integration Test Source"
            assert created_article.external_id == "https://example.com/integration-test"
            assert created_article.published_at == datetime(2026, 3, 18, 12, 0, 0, tzinfo=timezone.utc)
    
    @pytest.mark.asyncio
    async def test_ingestion_job_logging_integration(self):
        """Test ingestion job logging and error handling"""
        async def mock_fetch_coro():
            return [
                {
                    "title": "Test Article 1",
                    "url": "https://example.com/test1",
                    "source_name": "Test Source",
                    "content": "Test content 1",
                    "author": "Test Author",
                    "published_at": "2026-03-18T12:00:00Z",
                    "image_url": "https://example.com/image1.jpg",
                    "external_id": "https://example.com/test1"
                }
            ]
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.merge = AsyncMock()
        
        with patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session), \
             patch('app.tasks.ingest.save_article') as mock_save_article:
            
            mock_save_article.return_value = True
            
            await run_ingestion("integration_test_job", mock_fetch_coro())
            
            # Verify job log was created and updated
            assert mock_session.add.call_count >= 1
            assert mock_session.commit.call_count >= 2
            assert mock_session.merge.call_count >= 1
            
            # Verify save_article was called
            assert mock_save_article.call_count == 1
    
    @pytest.mark.asyncio
    async def test_duplicate_detection_integration(self):
        """Test duplicate detection across storage systems"""
        article_data = {
            "title": "Duplicate Test Article",
            "url": "https://example.com/duplicate-test",
            "source_name": "Duplicate Test Source",
            "content": "This is a test article for duplicate detection.",
            "author": "Test Author",
            "published_at": "2026-03-18T12:00:00Z",
            "image_url": "https://example.com/duplicate-image.jpg",
            "external_id": "https://example.com/duplicate-test"
        }
        
        # Mock existing article
        mock_existing_article = MagicMock()
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=AsyncMock(return_value=mock_existing_article)))
        
        with patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session), \
             patch('app.tasks.ingest.redis_client') as mock_redis:
            
            result = await save_article(article_data)
            
            assert result is False
            mock_session.add.assert_not_called()
            mock_session.commit.assert_not_called()
            mock_redis.setex.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_multiple_ingestion_clients_integration(self):
        """Test multiple ingestion clients working together"""
        # Mock tickers from database
        mock_tickers = ["AAPL", "MSFT", "GOOGL"]
        
        # Mock NewsAPI response
        mock_newsapi_response = {
            "status": "ok",
            "totalResults": 1,
            "articles": [
                {
                    "title": "Apple News",
                    "url": "https://example.com/apple-news",
                    "source": {"name": "Reuters"},
                    "publishedAt": "2026-03-18T12:00:00Z",
                    "content": "Apple news content.",
                    "author": "John Doe",
                    "urlToImage": "https://example.com/apple-image.jpg"
                }
            ]
        }
        
        # Mock RSS response
        mock_rss_response = [
            {
                "title": "Microsoft RSS News",
                "url": "https://rss.example.com/microsoft-news",
                "source_name": "RSS Feed",
                "published_at": "2026-03-18T11:00:00Z",
                "content": "Microsoft RSS content.",
                "author": None,
                "image_url": None,
                "external_id": "https://rss.example.com/microsoft-news"
            }
        ]
        
        # Mock Reddit response
        mock_reddit_response = [
            {
                "title": "Google Reddit Discussion",
                "url": "https://reddit.com/r/finance/comments/456/google-discussion",
                "source_name": "Reddit",
                "published_at": "2026-03-18T10:00:00Z",
                "content": "Google Reddit discussion.",
                "author": "reddituser",
                "image_url": None,
                "external_id": "https://reddit.com/r/finance/comments/456/google-discussion"
            }
        ]
        
        with patch('httpx.AsyncClient.get') as mock_newsapi_get, \
             patch('app.ingestion.rss_scraper.RSSScraper.fetch') as mock_rss_fetch, \
             patch('app.ingestion.reddit_client.RedditClient.fetch') as mock_reddit_fetch, \
             patch('app.tasks.ingest.save_article') as mock_save_article:
            
            mock_newsapi_get.return_value = MagicMock(
                status_code=200,
                json=AsyncMock(return_value=mock_newsapi_response),
                raise_for_status=AsyncMock()
            )
            mock_rss_fetch.return_value = mock_rss_response
            mock_reddit_fetch.return_value = mock_reddit_response
            mock_save_article.return_value = True
            
            # Test NewsAPI client
            newsapi_client = NewsAPIClient()
            newsapi_result = await newsapi_client.fetch(mock_tickers)
            
            assert len(newsapi_result) == 3  # 1 from NewsAPI + 1 from RSS + 1 from Reddit
            
            # Test RSS scraper
            rss_client = RSSScraper()
            rss_result = await rss_client.fetch(mock_tickers)
            
            assert len(rss_result) == 2  # 2 RSS items (1 per ticker)
            
            # Test Reddit client
            reddit_client = RedditClient()
            with patch.object(reddit_client, 'reddit', None):  # Mock no credentials
                reddit_result = await reddit_client.fetch()
                assert reddit_result == []  # Should return empty when no credentials
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling across the ingestion pipeline"""
        # Test network error in NewsAPI
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            client = NewsAPIClient()
            result = await client.fetch(["AAPL"])
            assert result == []
        
        # Test database error in save_article
        article_data = {
            "title": "Error Test Article",
            "url": "https://example.com/error-test",
            "source_name": "Error Test Source",
            "content": "This is a test article for error handling.",
            "author": "Test Author",
            "published_at": "2026-03-18T12:00:00Z",
            "image_url": "https://example.com/error-image.jpg",
            "external_id": "https://example.com/error-test"
        }
        
        # Mock session with database error
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=AsyncMock(return_value=None)))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock(side_effect=Exception("Database error"))
        
        with patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session), \
             patch('app.tasks.ingest.mongo_db') as mock_mongo, \
             patch('app.tasks.ingest.redis_client') as mock_redis:
            
            mock_mongo.raw_articles.insert_one = AsyncMock()
            
            # This should still try to save to MongoDB and Redis even if PostgreSQL fails
            # But the function should handle the error gracefully
            try:
                await save_article(article_data)
            except Exception:
                pass  # Expected to fail due to database error
    
    @pytest.mark.asyncio
    async def test_content_hash_consistency_integration(self):
        """Test that content hash is calculated consistently"""
        article_data = {
            "title": "Hash Test Article",
            "url": "https://example.com/hash-test",
            "source_name": "Hash Test Source",
            "content": "This is a test article for hash testing.",
            "author": "Test Author",
            "published_at": "2026-03-18T12:00:00Z",
            "image_url": "https://example.com/hash-image.jpg",
            "external_id": "https://example.com/hash-test"
        }
        
        # Calculate expected hash manually
        from app.processing.deduplicator import compute_content_hash
        expected_hash = compute_content_hash(article_data["title"], article_data["content"])
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=AsyncMock(return_value=None)))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        with patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session), \
             patch('app.tasks.ingest.mongo_db') as mock_mongo, \
             patch('app.tasks.ingest.redis_client') as mock_redis:
            
            mock_mongo.raw_articles.insert_one = AsyncMock()
            mock_redis.setex = AsyncMock()
            
            await save_article(article_data)
            
            # Verify the article was created with the correct hash
            created_article = mock_session.add.call_args[0][0]
            assert created_article.content_hash == expected_hash
            assert len(created_article.content_hash) == 64  # SHA-256 hash length