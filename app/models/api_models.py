from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class NewsArticleResponse(BaseModel):
    id: str
    title: str
    source_name: str
    source_url: str
    published_at: datetime
    summary: Optional[str]
    image_url: Optional[str]
    
    # Analysis fields
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
    impact_level: Optional[str] = None
    impact_score: Optional[float] = None
    ai_explanation: Optional[str] = None
    
    # Reliability
    reliability_score: Optional[float] = None
    
    # Tags
    tickers: List[str] = []
    sectors: List[str] = []

    class Config:
        from_attributes = True

class NewsFeedResponse(BaseModel):
    articles: List[NewsArticleResponse]
    count: int
    tier: str
