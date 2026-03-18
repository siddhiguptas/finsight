import praw
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.ingestion.base_client import BaseIngestionClient

logger = logging.getLogger(__name__)

class RedditClient(BaseIngestionClient):
    def __init__(self):
        self.reddit = None
        self.subreddits = ["stocks", "investing", "wallstreetbets", "finance"]
        self.posts_limit = 25
        self._initialize_reddit()

    def _initialize_reddit(self):
        """Initialize Reddit client if credentials are available."""
        if not all([settings.reddit_client_id, settings.reddit_client_secret]):
            logger.warning("Reddit API credentials missing. Reddit client will return empty results.")
            return

        try:
            self.reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent
            )
            # Test the connection
            self.reddit.auth.limits
            logger.info("Reddit client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}", exc_info=True)
            self.reddit = None

    async def fetch(self, subreddits: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetch posts from Reddit subreddits.
        
        Args:
            subreddits: List of subreddit names to fetch from. If None, uses default list.
            
        Returns:
            List of post dictionaries
        """
        if not self.reddit:
            logger.warning("Reddit client not initialized. Skipping Reddit fetch.")
            return []

        # Use provided subreddits or defaults
        target_subreddits = subreddits or self.subreddits
        
        if not target_subreddits:
            logger.warning("No subreddits specified for Reddit fetch.")
            return []

        # Process and validate subreddits
        processed_subreddits = self._process_subreddits(target_subreddits)
        if not processed_subreddits:
            logger.warning("No valid subreddits found after processing.")
            return []

        articles = []
        
        try:
            # PRAW is synchronous, run in thread pool
            loop = asyncio.get_event_loop()
            articles = await loop.run_in_executor(
                None, self._fetch_reddit_posts, processed_subreddits
            )
            
            logger.info(f"Reddit fetch completed. Found {len(articles)} posts from {len(processed_subreddits)} subreddits.")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching from Reddit: {e}", exc_info=True)
            return []

    def _process_subreddits(self, subreddits: List[str]) -> List[str]:
        """Process and validate subreddit names."""
        processed = []
        for subreddit in subreddits:
            if not subreddit or not subreddit.strip():
                continue
            # Clean subreddit name (remove r/ prefix if present)
            clean_name = subreddit.strip().lstrip('r/').lower()
            if clean_name and len(clean_name) >= 2:
                processed.append(clean_name)
            elif clean_name:
                logger.warning(f"Subreddit name too short: {clean_name}")
        
        return processed

    def _fetch_reddit_posts(self, subreddits: List[str]) -> List[Dict[str, Any]]:
        """Fetch posts from Reddit synchronously."""
        posts = []
        
        for subreddit_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Fetch hot posts
                for post in subreddit.hot(limit=self.posts_limit):
                    if self._should_skip_post(post):
                        continue
                    
                    processed_post = self._process_reddit_post(post, subreddit_name)
                    if processed_post:
                        posts.append(processed_post)
                        
            except Exception as e:
                logger.error(f"Error fetching from subreddit r/{subreddit_name}: {e}", exc_info=True)
        
        return posts

    def _should_skip_post(self, post) -> bool:
        """Determine if a post should be skipped."""
        # Skip stickied posts
        if getattr(post, 'stickied', False):
            return True
        
        # Skip posts without content or title
        title = getattr(post, 'title', '').strip()
        selftext = getattr(post, 'selftext', '').strip()
        
        if not title and not selftext:
            return True
        
        return False

    def _process_reddit_post(self, post, subreddit_name: str) -> Optional[Dict[str, Any]]:
        """Process a single Reddit post and extract required fields."""
        try:
            # Extract basic fields
            title = getattr(post, 'title', '').strip()
            permalink = getattr(post, 'permalink', '')
            post_id = getattr(post, 'id', '')
            
            if not title or not permalink or not post_id:
                logger.debug(f"Skipping post with missing required fields: {title}")
                return None

            # Build full URL
            full_url = f"https://reddit.com{permalink}"
            
            # Extract content (prefer selftext, fallback to title)
            content = getattr(post, 'selftext', '').strip()
            if not content:
                content = title
            
            # Extract author (handle None case)
            author = getattr(post, 'author', None)
            author_name = str(author) if author else "Unknown"
            
            # Convert timestamp
            created_utc = getattr(post, 'created_utc', 0)
            published_at = datetime.utcfromtimestamp(created_utc).isoformat()

            processed = {
                "title": title,
                "url": full_url,
                "source_name": f"Reddit r/{subreddit_name}",
                "published_at": published_at,
                "content": content,
                "author": author_name,
                "image_url": None,  # Reddit posts typically don't have image URLs in this context
                "external_id": post_id
            }
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing Reddit post: {e}", exc_info=True)
            return None

