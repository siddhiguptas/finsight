from fastapi import APIRouter, HTTPException

from app.models.live_models import FeedRequest, NewsFeedResponse, AnalyzeRequest, AnalyzeResponse
from app.services.news_fetcher import fetch_live_news, analyze_text

router = APIRouter()


@router.post("/feed", response_model=NewsFeedResponse)
async def live_feed(request: FeedRequest) -> NewsFeedResponse:
    if not request.tickers:
        raise HTTPException(status_code=400, detail="At least one ticker is required.")
    return await fetch_live_news(request)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_article(request: AnalyzeRequest) -> AnalyzeResponse:
    if not request.title or not request.content:
        raise HTTPException(status_code=400, detail="title and content are required.")
    return await analyze_text(request)
