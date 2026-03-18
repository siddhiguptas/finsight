import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from app.ingestion.reddit_client import RedditClient
from app.core.config import settings


class TestRedditClient:
    """Test the Reddit client for news ingestion"""
    
    def setup_method(self):
        """Set up test client for each test method"""
        self.client = RedditClient()
    
    def test_client_initialization_with_credentials(self):
        """Test that RedditClient initializes with valid credentials"""
        # Mock settings with valid credentials
        with patch.object(settings, 'reddit_client_id', 'test_client_id'), \
             patch.object(settings, 'reddit_client_secret', 'test_client_secret'):
            
            client = RedditClient()
            assert client.reddit is not None
            assert hasattr(client.reddit, 'subreddit')
    
    def test_client_initialization_without_credentials(self):
        """Test that RedditClient initializes without credentials"""
        # Mock settings without credentials
        with patch.object(settings, 'reddit_client_id', None), \
             patch.object(settings, 'reddit_client_secret', None):
            
            client = RedditClient()
            assert client.reddit is None
    
    @pytest.mark.asyncio
    async def test_fetch_without_credentials(self):
        """Test fetch returns empty list when credentials are missing"""
        # Mock settings without credentials
        with patch.object(settings, 'reddit_client_id', None), \
             patch.object(settings, 'reddit_client_secret', None):
            
            client = RedditClient()
            result = await client.fetch()
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_with_valid_credentials(self):
        """Test fetch with valid credentials and mock Reddit data"""
        # Mock settings with valid credentials
        with patch.object(settings, 'reddit_client_id', 'test_client_id'), \
             patch.object(settings, 'reddit_client_secret', 'test_client_secret'):
            
            client = RedditClient()
            
            # Mock Reddit post objects
            mock_post1 = Mock()
            mock_post1.title = "Apple Stock Analysis"
            mock_post1.permalink = "/r/stocks/comments/123/apple-stock-analysis"
            mock_post1.created_utc = 1710763200  # 2026-03-18 12:00:00 UTC
            mock_post1.selftext = "Detailed analysis of Apple stock performance."
            mock_post1.author = "investor123"
            mock_post1.id = "abc123"
            mock_post1.stickied = False
            
            mock_post2 = Mock()
            mock_post2.title = "Investing Tips for Beginners"
            mock_post2.permalink = "/r/investing/comments/456/investing-tips"
            mock_post2.created_utc = 1710759600  # 2026-03-18 11:00:00 UTC
            mock_post2.selftext = "Tips for new investors."
            mock_post2.author = "financeguru"
            mock_post2.id = "def456"
            mock_post2.stickied = False
            
            # Mock subreddit objects
            mock_subreddit1 = Mock()
            mock_subreddit1.hot.return_value = [mock_post1]
            
            mock_subreddit2 = Mock()
            mock_subreddit2.hot.return_value = [mock_post2]
            
            # Mock reddit object
            mock_reddit = Mock()
            mock_reddit.subreddit.side_effect = [mock_subreddit1, mock_subreddit2]
            
            client.reddit = mock_reddit
            
            result = await client.fetch()
            
            assert len(result) == 2
            assert result[0]["title"] == "Apple Stock Analysis"
            assert result[0]["source_name"] == "Reddit r/stocks"
            assert result[0]["external_id"] == "abc123"
            assert result[1]["title"] == "Investing Tips for Beginners"
            assert result[1]["source_name"] == "Reddit r/investing"
    
    @pytest.mark.asyncio
    async def test_fetch_skips_stickied_posts(self):
        """Test fetch skips stickied posts"""
        # Mock settings with valid credentials
        with patch.object(settings, 'reddit_client_id', 'test_client_id'), \
             patch.object(settings, 'reddit_client_secret', 'test_client_secret'):
            
            client = RedditClient()
            
            # Mock stickied post
            mock_stickied_post = Mock()
            mock_stickied_post.stickied = True
            
            # Mock normal post
            mock_normal_post = Mock()
            mock_normal_post.title = "Normal Post"
            mock_normal_post.permalink = "/r/stocks/comments/789/normal-post"
            mock_normal_post.created_utc = 1710763200
            mock_normal_post.selftext = "Normal content."
            mock_normal_post.author = "user123"
            mock_normal_post.id = "ghi789"
            mock_normal_post.stickied = False
            
            # Mock subreddit
            mock_subreddit = Mock()
            mock_subreddit.hot.return_value = [mock_stickied_post, mock_normal_post]
            
            mock_reddit = Mock()
            mock_reddit.subreddit.return_value = mock_subreddit
            
            client.reddit = mock_reddit
            
            result = await client.fetch()
            
            assert len(result) == 1
            assert result[0]["title"] == "Normal Post"
    
    @pytest.mark.asyncio
    async def test_fetch_with_custom_subreddits(self):
        """Test fetch with custom subreddit list"""
        # Mock settings with valid credentials
        with patch.object(settings, 'reddit_client_id', 'test_client_id'), \
             patch.object(settings, 'reddit_client_secret', 'test_client_secret'):
            
            client = RedditClient()
            
            # Mock post
            mock_post = Mock()
            mock_post.title = "Custom Subreddit Post"
            mock_post.permalink = "/r/custom/comments/123/custom-post"
            mock_post.created_utc = 1710763200
            mock_post.selftext = "Custom content."
            mock_post.author = "customuser"
            mock_post.id = "jkl123"
            mock_post.stickied = False
            
            mock_subreddit = Mock()
            mock_subreddit.hot.return_value = [mock_post]
            
            mock_reddit = Mock()
            mock_reddit.subreddit.return_value = mock_subreddit
            
            client.reddit = mock_reddit
            
            result = await client.fetch(["custom"])
            
            assert len(result) == 1
            assert result[0]["source_name"] == "Reddit r/custom"
    
    @pytest.mark.asyncio
    async def test_fetch_handles_reddit_errors(self):
        """Test fetch handles Reddit API errors gracefully"""
        # Mock settings with valid credentials
        with patch.object(settings, 'reddit_client_id', 'test_client_id'), \
             patch.object(settings, 'reddit_client_secret', 'test_client_secret'):
            
            client = RedditClient()
            
            # Mock reddit object that raises an exception
            mock_reddit = Mock()
            mock_reddit.subreddit.side_effect = Exception("Reddit API error")
            
            client.reddit = mock_reddit
            
            result = await client.fetch()
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_handles_empty_subreddit(self):
        """Test fetch handles empty subreddit results"""
        # Mock settings with valid credentials
        with patch.object(settings, 'reddit_client_id', 'test_client_id'), \
             patch.object(settings, 'reddit_client_secret', 'test_client_secret'):
            
            client = RedditClient()
            
            # Mock empty subreddit
            mock_subreddit = Mock()
            mock_subreddit.hot.return_value = []
            
            mock_reddit = Mock()
            mock_reddit.subreddit.return_value = mock_subreddit
            
            client.reddit = mock_reddit
            
            result = await client.fetch()
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_handles_missing_selftext(self):
        """Test fetch handles posts without selftext"""
        # Mock settings with valid credentials
        with patch.object(settings, 'reddit_client_id', 'test_client_id'), \
             patch.object(settings, 'reddit_client_secret', 'test_client_secret'):
            
            client = RedditClient()
            
            # Mock post without selftext
            mock_post = Mock()
            mock_post.title = "Post Without Selftext"
            mock_post.permalink = "/r/stocks/comments/123/post-without-selftext"
            mock_post.created_utc = 1710763200
            mock_post.selftext = ""  # Empty selftext
            mock_post.author = "user123"
            mock_post.id = "mno123"
            mock_post.stickied = False
            
            mock_subreddit = Mock()
            mock_subreddit.hot.return_value = [mock_post]
            
            mock_reddit = Mock()
            mock_reddit.subreddit.return_value = mock_subreddit
            
            client.reddit = mock_reddit
            
            result = await client.fetch()
            
            assert len(result) == 1
            assert result[0]["content"] == "Post Without Selftext"  # Should use title as content
    
    @pytest.mark.asyncio
    async def test_fetch_handles_missing_author(self):
        """Test fetch handles posts without author"""
        # Mock settings with valid credentials
        with patch.object(settings, 'reddit_client_id', 'test_client_id'), \
             patch.object(settings, 'reddit_client_secret', 'test_client_secret'):
            
            client = RedditClient()
            
            # Mock post without author
            mock_post = Mock()
            mock_post.title = "Post Without Author"
            mock_post.permalink = "/r/stocks/comments/123/post-without-author"
            mock_post.created_utc = 1710763200
            mock_post.selftext = "Content without author."
            mock_post.author = None
            mock_post.id = "pqr123"
            mock_post.stickied = False
            
            mock_subreddit = Mock()
            mock_subreddit.hot.return_value = [mock_post]
            
            mock_reddit = Mock()
            mock_reddit.subreddit.return_value = mock_subreddit
            
            client.reddit = mock_reddit
            
            result = await client.fetch()
            
            assert len(result) == 1
            assert result[0]["author"] == "None"  # Should convert None to string
    
    @pytest.mark.asyncio
    async def test_fetch_datetime_conversion(self):
        """Test fetch correctly converts Unix timestamp to ISO format"""
        # Mock settings with valid credentials
        with patch.object(settings, 'reddit_client_id', 'test_client_id'), \
             patch.object(settings, 'reddit_client_secret', 'test_client_secret'):
            
            client = RedditClient()
            
            # Mock post with specific timestamp
            mock_post = Mock()
            mock_post.title = "Test Post"
            mock_post.permalink = "/r/stocks/comments/123/test-post"
            mock_post.created_utc = 1710763200  # 2026-03-18 12:00:00 UTC
            mock_post.selftext = "Test content."
            mock_post.author = "testuser"
            mock_post.id = "stu123"
            mock_post.stickied = False
            
            mock_subreddit = Mock()
            mock_subreddit.hot.return_value = [mock_post]
            
            mock_reddit = Mock()
            mock_reddit.subreddit.return_value = mock_subreddit
            
            client.reddit = mock_reddit
            
            result = await client.fetch()
            
            assert len(result) == 1
            assert result[0]["published_at"] == "2026-03-18T12:00:00"
    
    @pytest.mark.asyncio
    async def test_fetch_multiple_posts_from_same_subreddit(self):
        """Test fetch handles multiple posts from the same subreddit"""
        # Mock settings with valid credentials
        with patch.object(settings, 'reddit_client_id', 'test_client_id'), \
             patch.object(settings, 'reddit_client_secret', 'test_client_secret'):
            
            client = RedditClient()
            
            # Mock multiple posts
            mock_post1 = Mock()
            mock_post1.title = "First Post"
            mock_post1.permalink = "/r/stocks/comments/123/first-post"
            mock_post1.created_utc = 1710763200
            mock_post1.selftext = "First content."
            mock_post1.author = "user1"
            mock_post1.id = "vwx123"
            mock_post1.stickied = False
            
            mock_post2 = Mock()
            mock_post2.title = "Second Post"
            mock_post2.permalink = "/r/stocks/comments/456/second-post"
            mock_post2.created_utc = 1710759600
            mock_post2.selftext = "Second content."
            mock_post2.author = "user2"
            mock_post2.id = "yz123"
            mock_post2.stickied = False
            
            mock_subreddit = Mock()
            mock_subreddit.hot.return_value = [mock_post1, mock_post2]
            
            mock_reddit = Mock()
            mock_reddit.subreddit.return_value = mock_subreddit
            
            client.reddit = mock_reddit
            
            result = await client.fetch(["stocks"])
            
            assert len(result) == 2
            assert result[0]["title"] == "First Post"
            assert result[1]["title"] == "Second Post"