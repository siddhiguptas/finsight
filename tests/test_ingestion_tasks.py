import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from celery import Celery
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.mongodb import mongo_db
from app.models.schemas import NewsArticle, TickerSectorMap, IngestionJobLog
from app.tasks.ingest import save_article, run_ingestion, fetch_newsapi, fetch_yahoo_rss, fetch_reddit, fetch_alpha_vantage, fetch_sec_edgar


class TestIngestionTasks:
    """Test the Celery ingestion tasks"""
    
    @pytest.mark.asyncio
    async def test_save_article_success(self):
        """Test successful article saving"""
        article_data = {
            "title": "Test Article",
            "url": "https://example.com/test",
            "source_name": "Test Source",
            "content": "Test content",
            "author": "Test Author",
            "published_at": "2026-03-18T12:00:00Z",
            "image_url": "https://example.com/image.jpg",
            "external_id": "https://example.com/test"
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
    
    @pytest.mark.asyncio
    async def test_save_article_duplicate(self):
        """Test article saving when duplicate exists"""
        article_data = {
            "title": "Test Article",
            "url": "https://example.com/test",
            "source_name": "Test Source",
            "content": "Test content",
            "author": "Test Author",
            "published_at": "2026-03-18T12:00:00Z",
            "image_url": "https://example.com/image.jpg",
            "external_id": "https://example.com/test"
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
    async def test_save_article_duplicate_hash(self):
        """Test article saving when content hash duplicate exists"""
        article_data = {
            "title": "Test Article",
            "url": "https://example.com/test",
            "source_name": "Test Source",
            "content": "Test content",
            "author": "Test Author",
            "published_at": "2026-03-18T12:00:00Z",
            "image_url": "https://example.com/image.jpg",
            "external_id": "https://example.com/different-url"
        }
        
        # Mock existing article with same hash
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
    async def test_save_article_processing_task_failure(self):
        """Test article saving when processing task fails"""
        article_data = {
            "title": "Test Article",
            "url": "https://example.com/test",
            "source_name": "Test Source",
            "content": "Test content",
            "author": "Test Author",
            "published_at": "2026-03-18T12:00:00Z",
            "image_url": "https://example.com/image.jpg",
            "external_id": "https://example.com/test"
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
            mock_process_task.delay.side_effect = Exception("Processing task failed")
            
            result = await save_article(article_data)
            
            # Should still return True even if processing task fails
            assert result is True
            mock_mongo.raw_articles.insert_one.assert_called_once()
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_redis.setex.assert_called_once()
            mock_process_task.delay.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_ingestion_success(self):
        """Test successful ingestion run"""
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
                },
                {
                    "title": "Test Article 2",
                    "url": "https://example.com/test2",
                    "source_name": "Test Source",
                    "content": "Test content 2",
                    "author": "Test Author",
                    "published_at": "2026-03-18T11:00:00Z",
                    "image_url": "https://example.com/image2.jpg",
                    "external_id": "https://example.com/test2"
                }
            ]
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.merge = AsyncMock()
        
        with patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session), \
             patch('app.tasks.ingest.save_article') as mock_save_article:
            
            mock_save_article.side_effect = [True, False]  # First succeeds, second is duplicate
            
            await run_ingestion("test_job", mock_fetch_coro())
            
            # Verify job log was created and updated
            assert mock_session.add.call_count >= 1
            assert mock_session.commit.call_count >= 2
            assert mock_session.merge.call_count >= 1
            
            # Verify save_article was called for each article
            assert mock_save_article.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_ingestion_failure(self):
        """Test ingestion run failure"""
        async def mock_fetch_coro():
            raise Exception("Fetch failed")
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.merge = AsyncMock()
        
        with patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session):
            
            await run_ingestion("test_job", mock_fetch_coro())
            
            # Verify job log was created and updated with error
            assert mock_session.add.call_count >= 1
            assert mock_session.commit.call_count >= 2
            assert mock_session.merge.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_fetch_newsapi_task(self):
        """Test NewsAPI fetch task"""
        with patch('app.tasks.ingest.NewsAPIClient') as mock_client_class, \
             patch('app.tasks.ingest.run_ingestion') as mock_run_ingestion, \
             patch('app.tasks.ingest.asyncio.run') as mock_asyncio_run:
            
            mock_client = AsyncMock()
            mock_client.fetch = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client
            
            # Mock database query
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value = MagicMock(scalar_one_or_none=AsyncMock(return_value=None))
            
            with patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session):
                result = fetch_newsapi()
                
                assert result == {"status": "done"}
                mock_client_class.assert_called_once()
                mock_run_ingestion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_yahoo_rss_task(self):
        """Test Yahoo RSS fetch task"""
        with patch('app.tasks.ingest.RSSScraper') as mock_client_class, \
             patch('app.tasks.ingest.run_ingestion') as mock_run_ingestion, \
             patch('app.tasks.ingest.asyncio.run') as mock_asyncio_run:
            
            mock_client = AsyncMock()
            mock_client.fetch = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client
            
            # Mock database query
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value = MagicMock(scalar_one_or_none=AsyncMock(return_value=None))
            
            with patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session):
                result = fetch_yahoo_rss()
                
                assert result == {"status": "done"}
                mock_client_class.assert_called_once()
                mock_run_ingestion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_reddit_task(self):
        """Test Reddit fetch task"""
        with patch('app.tasks.ingest.RedditClient') as mock_client_class, \
             patch('app.tasks.ingest.run_ingestion') as mock_run_ingestion, \
             patch('app.tasks.ingest.asyncio.run') as mock_asyncio_run:
            
            mock_client = AsyncMock()
            mock_client.fetch = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client
            
            result = fetch_reddit()
            
            assert result == {"status": "done"}
            mock_client_class.assert_called_once()
            mock_run_ingestion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_alpha_vantage_task(self):
        """Test Alpha Vantage fetch task"""
        with patch('app.tasks.ingest.AlphaVantageClient') as mock_client_class, \
             patch('app.tasks.ingest.run_ingestion') as mock_run_ingestion, \
             patch('app.tasks.ingest.asyncio.run') as mock_asyncio_run:
            
            mock_client = AsyncMock()
            mock_client.fetch = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client
            
            # Mock database query
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value = MagicMock(scalar_one_or_none=AsyncMock(return_value=None))
            
            with patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session):
                result = fetch_alpha_vantage()
                
                assert result == {"status": "done"}
                mock_client_class.assert_called_once()
                mock_run_ingestion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_sec_edgar_task(self):
        """Test SEC EDGAR fetch task"""
        with patch('app.tasks.ingest.SECEdgarClient') as mock_client_class, \
             patch('app.tasks.ingest.run_ingestion') as mock_run_ingestion, \
             patch('app.tasks.ingest.asyncio.run') as mock_asyncio_run:
            
            mock_client = AsyncMock()
            mock_client.fetch = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client
            
            # Mock database query
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value = MagicMock(scalar_one_or_none=AsyncMock(return_value=None))
            
            with patch('app.tasks.ingest.AsyncSessionLocal', return_value=mock_session):
                result = fetch_sec_edgar()
                
                assert result == {"status": "done"}
                mock_client_class.assert_called_once()
                mock_run_ingestion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_article_published_at_parsing(self):
        """Test published_at field parsing in different formats"""
        test_cases = [
            {
                "published_at": "2026-03-18T12:00:00Z",
                "expected": datetime(2026, 3, 18, 12, 0, 0, tzinfo=timezone.utc)
            },
            {
                "published_at": "Wed, 18 Mar 2026 12:00:00 GMT",
                "expected": datetime(2026, 3, 18, 12, 0, 0, tzinfo=timezone.utc)
            },
            {
                "published_at": None,
                "expected": datetime.utcnow().replace(microsecond=0)  # Should use current time
            },
            {
                "published_at": "invalid-date",
                "expected": datetime.utcnow().replace(microsecond=0)  # Should fallback to current time
            }
        ]
        
        for test_case in test_cases:
            article_data = {
                "title": "Test Article",
                "url": "https://example.com/test",
                "source_name": "Test Source",
                "content": "Test content",
                "author": "Test Author",
                "published_at": test_case["published_at"],
                "image_url": "https://example.com/image.jpg",
                "external_id": "https://example.com/test"
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
                mock_session.add.assert_called_once()
                
                # Get the created article object
                created_article = mock_session.add.call_args[0][0]
                
                # For invalid dates, we can't easily test the exact time, so just check it's recent
                if test_case["published_at"] in [None, "invalid-date"]:
                    time_diff = abs((created_article.published_at - datetime.utcnow().replace(microsecond=0)).total_seconds())
                    assert time_diff < 5  # Should be within 5 seconds
                else:
                    assert created_article.published_at == test_case["expected"]