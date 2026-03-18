import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from app.core.database import AsyncSessionLocal
from app.core.mongodb import mongo_db
from app.models.schemas import NewsArticle, TickerSectorMap, IngestionJobLog
from app.tasks.ingest import fetch_newsapi, fetch_yahoo_rss, fetch_reddit, fetch_alpha_vantage, fetch_sec_edgar


class TestIngestionE2E:
    """End-to-end tests for the ingestion pipeline"""
    
    @pytest.mark.asyncio
    async def test_complete_newsapi_ingestion_pipeline(self):
        """Test complete NewsAPI ingestion pipeline from fetch to storage"""
        # Mock tickers from database
        mock_tickers = ["AAPL", "MSFT"]
        
        # Mock NewsAPI response
        mock_newsapi_response = {
            "status": "ok",
            "totalResults": 2,
            "articles": [
                {
                    "title": "Apple Reports Record Earnings",
                    "url": "https://reuters.com/apple-earnings",
                    "source": {"name": "Reuters"},
                    "publishedAt": "2026-03-18T12:00:00Z",
                    "content": "Apple reports record earnings this quarter.",
                    "author": "John Doe",
                    "urlToImage": "https://reuters.com/apple-image.jpg"
                },
                {
                    "title": "Microsoft Announces New AI Features",
                    "url": "https://bloomberg.com/microsoft-ai",
                    "source": {"name": "Bloomberg"},
                    "publishedAt": "2026-03-18T11:30:00Z",
                    "content": "Microsoft announces new AI features for Office.",
                    "author": "Jane Smith",
                    "urlToImage": None
                }
            ]
        }
        
        # Mock MongoDB insert
        mock_mongo_insert = AsyncMock()
        mock_mongo_insert.inserted_id = "mock_mongo_id_1"
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        
        # Mock session for database operations
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=AsyncMock(return_value=None)))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.merge = AsyncMock()
        
        with patch('httpx.AsyncClient.get') as mock_newsapi_get, \
             patch('app.tasks.ingest.mongo_db') as mock_mongo, \
             patch('app.tasks.ingest.redis_client', mock_redis), \
             patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session), \
             patch('app.tasks.ingest.process_article') as mock_process_task, \
             patch('app.tasks.ingest.NewsAPIClient') as mock_client_class, \
             patch('app.tasks.ingest.run_ingestion') as mock_run_ingestion:
            
            # Configure NewsAPI mock
            mock_newsapi_get.return_value = MagicMock(
                status_code=200,
                json=AsyncMock(return_value=mock_newsapi_response),
                raise_for_status=AsyncMock()
            )
            
            # Configure MongoDB mock
            mock_mongo.raw_articles.insert_one = AsyncMock(return_value=mock_mongo_insert)
            
            # Configure NewsAPI client mock
            mock_client = AsyncMock()
            mock_client.fetch = AsyncMock(return_value=mock_newsapi_response["articles"])
            mock_client_class.return_value = mock_client
            
            # Configure run_ingestion mock
            mock_run_ingestion.return_value = None
            
            # Execute the task
            result = fetch_newsapi()
            
            # Verify task completed successfully
            assert result == {"status": "done"}
            mock_client_class.assert_called_once()
            mock_run_ingestion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_rss_ingestion_pipeline(self):
        """Test complete RSS ingestion pipeline from fetch to storage"""
        # Mock tickers from database
        mock_tickers = ["AAPL", "MSFT"]
        
        # Mock RSS responses
        mock_yahoo_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        <channel>
        <title>Yahoo Finance: AAPL</title>
        <item>
        <title>Apple Stock Analysis</title>
        <link>https://finance.yahoo.com/apple-analysis</link>
        <pubDate>Wed, 18 Mar 2026 12:00:00 GMT</pubDate>
        <description>Apple stock analysis content.</description>
        </item>
        </channel>
        </rss>"""
        
        mock_google_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        <channel>
        <title>Google News: AAPL</title>
        <item>
        <title>Apple News Update</title>
        <link>https://news.google.com/apple-update</link>
        <pubDate>Wed, 18 Mar 2026 11:30:00 GMT</pubDate>
        <description>Apple news update content.</description>
        </item>
        </channel>
        </rss>"""
        
        # Mock MongoDB insert
        mock_mongo_insert = AsyncMock()
        mock_mongo_insert.inserted_id = "mock_mongo_id_2"
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        
        # Mock session for database operations
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=AsyncMock(return_value=None)))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.merge = AsyncMock()
        
        with patch('httpx.AsyncClient.get') as mock_get, \
             patch('app.tasks.ingest.mongo_db') as mock_mongo, \
             patch('app.tasks.ingest.redis_client', mock_redis), \
             patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session), \
             patch('app.tasks.ingest.process_article') as mock_process_task, \
             patch('app.tasks.ingest.RSSScraper') as mock_client_class, \
             patch('app.tasks.ingest.run_ingestion') as mock_run_ingestion:
            
            # Configure RSS mocks
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
            
            # Configure MongoDB mock
            mock_mongo.raw_articles.insert_one = AsyncMock(return_value=mock_mongo_insert)
            
            # Configure RSS client mock
            mock_client = AsyncMock()
            mock_client.fetch = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client
            
            # Configure run_ingestion mock
            mock_run_ingestion.return_value = None
            
            # Execute the task
            result = fetch_yahoo_rss()
            
            # Verify task completed successfully
            assert result == {"status": "done"}
            mock_client_class.assert_called_once()
            mock_run_ingestion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_reddit_ingestion_pipeline(self):
        """Test complete Reddit ingestion pipeline from fetch to storage"""
        # Mock Reddit post objects
        mock_post = Mock()
        mock_post.title = "Reddit Finance Discussion"
        mock_post.permalink = "/r/finance/comments/123/finance-discussion"
        mock_post.created_utc = 1710763200  # 2026-03-18 12:00:00 UTC
        mock_post.selftext = "Finance discussion content."
        mock_post.author = "financeuser"
        mock_post.id = "abc123"
        mock_post.stickied = False
        
        # Mock subreddit
        mock_subreddit = Mock()
        mock_subreddit.hot.return_value = [mock_post]
        
        # Mock reddit object
        mock_reddit = Mock()
        mock_reddit.subreddit.return_value = mock_subreddit
        
        # Mock MongoDB insert
        mock_mongo_insert = AsyncMock()
        mock_mongo_insert.inserted_id = "mock_mongo_id_3"
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        
        # Mock session for database operations
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=AsyncMock(return_value=None)))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.merge = AsyncMock()
        
        with patch('app.tasks.ingest.mongo_db') as mock_mongo, \
             patch('app.tasks.ingest.redis_client', mock_redis), \
             patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session), \
             patch('app.tasks.ingest.process_article') as mock_process_task, \
             patch('app.tasks.ingest.RedditClient') as mock_client_class, \
             patch('app.tasks.ingest.run_ingestion') as mock_run_ingestion:
            
            # Configure Reddit client mock with valid credentials
            with patch('app.core.config.settings.reddit_client_id', 'test_client_id'), \
                 patch('app.core.config.settings.reddit_client_secret', 'test_client_secret'):
                
                mock_client = AsyncMock()
                mock_client.fetch = AsyncMock(return_value=[{
                    "title": "Reddit Finance Discussion",
                    "url": "https://reddit.com/r/finance/comments/123/finance-discussion",
                    "source_name": "Reddit r/finance",
                    "published_at": "2026-03-18T12:00:00",
                    "content": "Finance discussion content.",
                    "author": "financeuser",
                    "external_id": "abc123"
                }])
                mock_client_class.return_value = mock_client
                
                # Configure MongoDB mock
                mock_mongo.raw_articles.insert_one = AsyncMock(return_value=mock_mongo_insert)
                
                # Configure run_ingestion mock
                mock_run_ingestion.return_value = None
                
                # Execute the task
                result = fetch_reddit()
                
                # Verify task completed successfully
                assert result == {"status": "done"}
                mock_client_class.assert_called_once()
                mock_run_ingestion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ingestion_pipeline_error_handling(self):
        """Test error handling across the entire ingestion pipeline"""
        # Test NewsAPI task with network error
        with patch('app.tasks.ingest.NewsAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.fetch = AsyncMock(side_effect=Exception("Network error"))
            mock_client_class.return_value = mock_client
            
            with patch('app.tasks.ingest.run_ingestion') as mock_run_ingestion:
                mock_run_ingestion.return_value = None
                
                result = fetch_newsapi()
                assert result == {"status": "done"}  # Task should still complete even with errors
        
        # Test RSS task with invalid XML
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                text="Invalid XML content",
                raise_for_status=AsyncMock()
            )
            
            with patch('app.tasks.ingest.RSSScraper') as mock_client_class, \
                 patch('app.tasks.ingest.run_ingestion') as mock_run_ingestion:
                
                mock_client = AsyncMock()
                mock_client.fetch = AsyncMock(return_value=[])
                mock_client_class.return_value = mock_client
                mock_run_ingestion.return_value = None
                
                result = fetch_yahoo_rss()
                assert result == {"status": "done"}
        
        # Test Reddit task without credentials
        with patch('app.tasks.ingest.RedditClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.fetch = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client
            
            with patch('app.tasks.ingest.run_ingestion') as mock_run_ingestion:
                mock_run_ingestion.return_value = None
                
                result = fetch_reddit()
                assert result == {"status": "done"}
    
    @pytest.mark.asyncio
    async def test_ingestion_pipeline_performance(self):
        """Test ingestion pipeline performance with realistic data volumes"""
        # Mock large number of articles
        mock_articles = []
        for i in range(50):
            mock_articles.append({
                "title": f"Article {i}",
                "url": f"https://example.com/article{i}",
                "source_name": "Test Source",
                "content": f"Content for article {i}",
                "author": f"Author {i}",
                "published_at": "2026-03-18T12:00:00Z",
                "image_url": f"https://example.com/image{i}.jpg",
                "external_id": f"https://example.com/article{i}"
            })
        
        # Mock MongoDB insert
        mock_mongo_insert = AsyncMock()
        mock_mongo_insert.inserted_id = "mock_mongo_id"
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        
        # Mock session for database operations
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=AsyncMock(return_value=None)))
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.merge = AsyncMock()
        
        with patch('app.tasks.ingest.mongo_db') as mock_mongo, \
             patch('app.tasks.ingest.redis_client', mock_redis), \
             patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session), \
             patch('app.tasks.ingest.process_article') as mock_process_task:
            
            mock_mongo.raw_articles.insert_one = AsyncMock(return_value=mock_mongo_insert)
            
            # Test saving multiple articles
            start_time = datetime.utcnow()
            
            for article_data in mock_articles:
                result = await save_article(article_data)
                assert result is True
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Verify all articles were processed
            assert mock_mongo.raw_articles.insert_one.call_count == 50
            assert mock_session.add.call_count == 50
            assert mock_session.commit.call_count == 50
            assert mock_redis.setex.call_count == 50
            assert mock_process_task.delay.call_count == 50
            
            # Performance should be reasonable (less than 10 seconds for 50 articles)
            assert duration < 10.0
    
    @pytest.mark.asyncio
    async def test_ingestion_pipeline_data_consistency(self):
        """Test data consistency across the entire ingestion pipeline"""
        article_data = {
            "title": "Consistency Test Article",
            "url": "https://example.com/consistency-test",
            "source_name": "Consistency Test Source",
            "content": "This is a test article for data consistency testing.",
            "author": "Consistency Test Author",
            "published_at": "2026-03-18T12:00:00Z",
            "image_url": "https://example.com/consistency-image.jpg",
            "external_id": "https://example.com/consistency-test"
        }
        
        # Calculate expected hash
        from app.processing.deduplicator import compute_content_hash
        expected_hash = compute_content_hash(article_data["title"], article_data["content"])
        
        # Mock MongoDB insert
        mock_mongo_insert = AsyncMock()
        mock_mongo_insert.inserted_id = "mock_mongo_id"
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        
        # Mock session for database operations
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
            
            # Verify data consistency
            created_article = mock_session.add.call_args[0][0]
            
            # Check all fields are correctly stored
            assert created_article.title == article_data["title"]
            assert created_article.source_name == article_data["source_name"]
            assert created_article.url == article_data["url"]
            assert created_article.summary == article_data["content"][:500]
            assert created_article.full_text_ref == "mock_mongo_id"
            assert created_article.author == article_data["author"]
            assert created_article.published_at == datetime(2026, 3, 18, 12, 0, 0, tzinfo=timezone.utc)
            assert created_article.content_hash == expected_hash
            assert created_article.image_url == article_data["image_url"]
            assert created_article.external_id == article_data["external_id"]
            
            # Verify MongoDB storage
            mock_mongo.raw_articles.insert_one.assert_called_once_with({
                "source": article_data["source_name"],
                "url": article_data["url"],
                "title": article_data["title"],
                "full_text": article_data["content"],
                "scraped_at": mock_session.commit.call_args[0][0].scraped_at  # Mock datetime
            })
            
            # Verify Redis caching
            mock_redis.setex.assert_called_once_with(f"dedup:hash:{expected_hash}", 172800, "1")
            
            # Verify processing task was enqueued
            mock_process_task.delay.assert_called_once_with(str(created_article.id))
    
    @pytest.mark.asyncio
    async def test_ingestion_pipeline_concurrency(self):
        """Test ingestion pipeline behavior under concurrent access"""
        # Create multiple articles that might have similar content
        articles = [
            {
                "title": "Concurrent Test Article 1",
                "url": "https://example.com/concurrent-test-1",
                "source_name": "Concurrent Test Source",
                "content": "This is the first concurrent test article.",
                "author": "Concurrent Author 1",
                "published_at": "2026-03-18T12:00:00Z",
                "image_url": "https://example.com/concurrent-image-1.jpg",
                "external_id": "https://example.com/concurrent-test-1"
            },
            {
                "title": "Concurrent Test Article 2",
                "url": "https://example.com/concurrent-test-2",
                "source_name": "Concurrent Test Source",
                "content": "This is the second concurrent test article.",
                "author": "Concurrent Author 2",
                "published_at": "2026-03-18T12:01:00Z",
                "image_url": "https://example.com/concurrent-image-2.jpg",
                "external_id": "https://example.com/concurrent-test-2"
            }
        ]
        
        # Mock MongoDB insert
        mock_mongo_insert = AsyncMock()
        mock_mongo_insert.inserted_id = "mock_mongo_id"
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        
        # Mock session for database operations
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
            
            # Simulate concurrent saves
            tasks = []
            for article_data in articles:
                task = save_article(article_data)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # Both articles should be saved successfully
            assert all(results)
            
            # Verify both articles were stored
            assert mock_mongo.raw_articles.insert_one.call_count == 2
            assert mock_session.add.call_count == 2
            assert mock_session.commit.call_count == 2
            assert mock_redis.setex.call_count == 2
            assert mock_process_task.delay.call_count == 2
    
    @pytest.mark.asyncio
    async def test_ingestion_pipeline_cleanup(self):
        """Test cleanup and resource management in the ingestion pipeline"""
        article_data = {
            "title": "Cleanup Test Article",
            "url": "https://example.com/cleanup-test",
            "source_name": "Cleanup Test Source",
            "content": "This is a test article for cleanup testing.",
            "author": "Cleanup Test Author",
            "published_at": "2026-03-18T12:00:00Z",
            "image_url": "https://example.com/cleanup-image.jpg",
            "external_id": "https://example.com/cleanup-test"
        }
        
        # Mock MongoDB insert
        mock_mongo_insert = AsyncMock()
        mock_mongo_insert.inserted_id = "mock_mongo_id"
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        
        # Mock session for database operations
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
            
            # Verify that database session was properly managed
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once()
            
            # Verify that MongoDB and Redis operations completed
            mock_mongo.raw_articles.insert_one.assert_called_once()
            mock_redis.setex.assert_called_once()
            
            # Verify that processing task was enqueued
            mock_process_task.delay.assert_called_once()
            
            # Verify that no resources were leaked (all mocks were called as expected)
            assert mock_session.add.call_count == 1
            assert mock_session.commit.call_count == 1
            assert mock_session.refresh.call_count == 1
            assert mock_mongo.raw_articles.insert_one.call_count == 1
            assert mock_redis.setex.call_count == 1
            assert mock_process_task.delay.call_count == 1