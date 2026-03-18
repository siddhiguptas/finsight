import praw
import asyncio
from datetime import datetime
from app.core.config import settings
from app.ingestion.base_client import BaseIngestionClient

class RedditClient(BaseIngestionClient):
    def __init__(self):
        self.reddit = None
        if all([settings.reddit_client_id, settings.reddit_client_secret]):
            self.reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent
            )

    async def fetch(self, subreddits: list[str] = ["stocks", "investing"]):
        if not self.reddit:
            print("Reddit API credentials missing.")
            return []

        articles = []
        
        def get_reddit_posts():
            posts = []
            for sub in subreddits:
                subreddit = self.reddit.subreddit(sub)
                for post in subreddit.hot(limit=25):
                    if post.stickied: continue
                    posts.append({
                        "title": post.title,
                        "url": f"https://reddit.com{post.permalink}",
                        "source_name": f"Reddit r/{sub}",
                        "published_at": datetime.utcfromtimestamp(post.created_utc).isoformat(),
                        "content": post.selftext or post.title,
                        "author": str(post.author),
                        "external_id": post.id
                    })
            return posts

        # PRAW is synchronous, run in thread pool
        try:
            loop = asyncio.get_event_loop()
            articles = await loop.run_in_executor(None, get_reddit_posts)
        except Exception as e:
            print(f"Error fetching from Reddit: {e}")

        return articles

