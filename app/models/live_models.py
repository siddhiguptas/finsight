from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, validator

AnalysisMode = Literal["none", "fast", "full"]
ExplanationDetail = Literal["short", "medium", "detailed"]
ExplanationFormat = Literal["paragraph", "bullets"]


class FeedRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, description="List of stock tickers")
    company_names: Optional[List[str]] = Field(default=None)
    market: Optional[str] = Field(default=None, description="Market code, e.g. US, IN")
    time_window_hours: int = Field(default=24, ge=1, le=168)
    limit: int = Field(default=20, ge=1, le=50)
    sources: Optional[List[str]] = Field(default=None)
    analysis_mode: AnalysisMode = Field(default="fast")
    explanation_detail: ExplanationDetail = Field(default="medium")
    explanation_format: ExplanationFormat = Field(default="paragraph")

    @validator("tickers", pre=True)
    def _normalize_tickers(cls, value: List[str]) -> List[str]:
        cleaned = [t.strip().upper() for t in value if t and t.strip()]
        if not cleaned:
            raise ValueError("At least one ticker is required.")
        return cleaned

    @validator("company_names", pre=True)
    def _normalize_company_names(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if not value:
            return None
        cleaned = [n.strip() for n in value if n and n.strip()]
        return cleaned or None

    @validator("market", pre=True)
    def _normalize_market(cls, value: Optional[str]) -> Optional[str]:
        return value.strip().upper() if value else None

    @validator("sources", pre=True)
    def _normalize_sources(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if not value:
            return None
        cleaned = [s.strip().lower() for s in value if s and s.strip()]
        return cleaned or None


class AnalyzeRequest(BaseModel):
    title: str
    content: str
    ticker: Optional[str] = None
    analysis_mode: AnalysisMode = Field(default="full")
    explanation_detail: ExplanationDetail = Field(default="medium")
    explanation_format: ExplanationFormat = Field(default="paragraph")

    @validator("ticker", pre=True)
    def _normalize_ticker(cls, value: Optional[str]) -> Optional[str]:
        return value.strip().upper() if value else None


class NewsArticleOut(BaseModel):
    id: str
    title: str
    source_name: str
    source_url: str
    published_at: datetime
    summary: Optional[str] = None
    image_url: Optional[str] = None
    tickers: List[str] = []
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
    impact_level: Optional[str] = None
    impact_score: Optional[float] = None
    ai_explanation: Optional[str] = None
    ai_explanation_is_fallback: Optional[bool] = None


class NewsFeedResponse(BaseModel):
    articles: List[NewsArticleOut]
    count: int


class AnalyzeResponse(BaseModel):
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
    impact_level: Optional[str] = None
    impact_score: Optional[float] = None
    ai_explanation: Optional[str] = None
    ai_explanation_is_fallback: Optional[bool] = None
