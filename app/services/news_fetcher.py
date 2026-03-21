import asyncio
import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Iterable, List, Optional

import feedparser
import httpx
from urllib.parse import quote_plus

from app.core.config import settings
from app.models.live_models import FeedRequest, NewsFeedResponse, NewsArticleOut, AnalyzeRequest, AnalyzeResponse
from app.processing.sentiment_engine import classify_sentiment, compute_impact_score, generate_explanation

DEFAULT_SOURCES = ["newsapi", "yahoo_rss", "google_news_rss"]
ANALYSIS_CONCURRENCY = 3
REQUEST_TIMEOUT = 12.0


@dataclass
class NormalizedArticle:
    id: str
    title: str
    source_name: str
    source_url: str
    published_at: datetime
    summary: str
    image_url: Optional[str]
    content: str
    tickers: List[str]




def normalize_url(url: str) -> str:
    cleaned = url.strip().lower()
    cleaned = re.sub(r"^https?://", "", cleaned)
    cleaned = cleaned.split("#")[0]
    return cleaned.rstrip("/")


def compute_content_hash(title: str, content: str) -> str:
    text = f"{title} {content or ''}".lower()
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"[^a-z0-9 ]", "", text)[:500]
    return hashlib.sha256(text.encode()).hexdigest()


def _safe_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, tuple):
        try:
            return datetime(*value[:6], tzinfo=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)
    if not value:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            dt = parsedate_to_datetime(str(value))
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)


def _summary_from_content(content: str, max_len: int = 500) -> str:
    text = re.sub(r"\s+", " ", (content or "").strip())
    return text[:max_len] if text else ""


def _match_tickers_and_names(text: str, tickers: List[str], company_names: Optional[List[str]]) -> List[str]:
    if not text:
        return []
    upper_text = text.upper()
    matched = []
    for ticker in tickers:
        pattern = rf"(?<![A-Z0-9])\$?{re.escape(ticker)}(?![A-Z0-9])"
        if re.search(pattern, upper_text):
            matched.append(ticker)
    if matched:
        return matched
    if company_names:
        lower_text = text.lower()
        for name in company_names:
            if name.lower() in lower_text:
                return tickers
    return []


async def fetch_newsapi(req: FeedRequest) -> List[NormalizedArticle]:
    if not settings.newsapi_key:
        return []
    if not req.tickers:
        return []

    query_terms = []
    for ticker in req.tickers:
        query_terms.extend([f"\"{ticker}\"", f"${ticker}"])
    if req.company_names:
        query_terms.extend([f"\"{name}\"" for name in req.company_names])
    query = " OR ".join(query_terms)

    from_date = (datetime.now(timezone.utc) - timedelta(hours=req.time_window_hours)).isoformat()
    params = {
        "q": query,
        "from": from_date,
        "sortBy": "publishedAt",
        "apiKey": settings.newsapi_key,
        "language": "en",
        "pageSize": 100,
    }

    articles: List[NormalizedArticle] = []
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            resp = await client.get("https://newsapi.org/v2/everything", params=params)
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            return []

    for article in payload.get("articles", []):
        title = (article.get("title") or "").strip()
        url = (article.get("url") or "").strip()
        if not title or not url:
            continue
        content = article.get("content") or article.get("description") or ""
        matched = _match_tickers_and_names(
            f"{title} {content}", req.tickers, req.company_names
        )
        if not matched:
            continue
        published_at = _safe_datetime(article.get("publishedAt"))
        source_name = article.get("source", {}).get("name") or "NewsAPI"
        normalized_url = normalize_url(url)
        article_id = hashlib.sha256(normalized_url.encode()).hexdigest()
        articles.append(
            NormalizedArticle(
                id=article_id,
                title=title,
                source_name=source_name,
                source_url=url,
                published_at=published_at,
                summary=_summary_from_content(content),
                image_url=article.get("urlToImage"),
                content=content,
                tickers=matched,
            )
        )
    return articles


def _rss_country_params(market: Optional[str]) -> Dict[str, str]:
    if not market:
        return {"hl": "en-US", "gl": "US", "ceid": "US:en"}
    market = market.upper()
    return {"hl": f"en-{market}", "gl": market, "ceid": f"{market}:en"}


async def _fetch_rss(url: str, source_name: str, tickers: List[str]) -> List[NormalizedArticle]:
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except Exception:
            return []

    feed = feedparser.parse(resp.text)
    articles: List[NormalizedArticle] = []
    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        if not title or not link:
            continue
        published_at = _safe_datetime(
            getattr(entry, "published", None)
            or getattr(entry, "updated", None)
            or getattr(entry, "published_parsed", None)
            or getattr(entry, "updated_parsed", None)
        )
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        normalized_url = normalize_url(link)
        article_id = hashlib.sha256(normalized_url.encode()).hexdigest()
        articles.append(
            NormalizedArticle(
                id=article_id,
                title=title,
                source_name=source_name,
                source_url=link,
                published_at=published_at,
                summary=_summary_from_content(summary),
                image_url=None,
                content=summary or title,
                tickers=tickers,
            )
        )
    return articles


async def fetch_yahoo_rss(req: FeedRequest) -> List[NormalizedArticle]:
    tasks = [
        _fetch_rss(
            f"https://finance.yahoo.com/rss/headline?s={ticker}",
            "Yahoo Finance",
            [ticker],
        )
        for ticker in req.tickers
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [article for batch in results if isinstance(batch, list) for article in batch]


async def fetch_google_news_rss(req: FeedRequest) -> List[NormalizedArticle]:
    params = _rss_country_params(req.market)
    base = "https://news.google.com/rss/search"
    tasks = []
    for ticker in req.tickers:
        query = f"{ticker} stock news"
        url = (
            f"{base}?q={quote_plus(query)}"
            f"&hl={params['hl']}&gl={params['gl']}&ceid={params['ceid']}"
        )
        tasks.append(_fetch_rss(url, "Google News", [ticker]))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [article for batch in results if isinstance(batch, list) for article in batch]


async def _analyze_article(
    article: NormalizedArticle,
    analysis_mode: str,
    semaphore: asyncio.Semaphore,
    ticker_hint: Optional[str],
    explanation_detail: str,
    explanation_format: str,
) -> Dict[str, Optional[Any]]:
    if analysis_mode == "none":
        return {
            "sentiment_label": None,
            "sentiment_score": None,
            "impact_level": None,
            "impact_score": None,
            "ai_explanation": None,
            "ai_explanation_is_fallback": None,
        }

    async with semaphore:
        text = f"{article.title}. {article.content or ''}"
        sentiment = await classify_sentiment(text)
        impact_score, impact_level = await compute_impact_score(
            sentiment_score=sentiment["score"],
            title=article.title,
            is_primary=True,
            source_credibility=0.5,
        )
        explanation = None
        explanation_is_fallback = None
        if analysis_mode == "full":
            explanation, explanation_is_fallback = await generate_explanation(
                article.title,
                article.content or article.summary,
                ticker_hint or (article.tickers[0] if article.tickers else "MARKET"),
                sentiment["label"],
                detail=explanation_detail,
                format_style=explanation_format,
            )

    return {
        "sentiment_label": sentiment["label"],
        "sentiment_score": sentiment["score"],
        "impact_level": impact_level,
        "impact_score": impact_score,
        "ai_explanation": explanation,
        "ai_explanation_is_fallback": explanation_is_fallback,
    }


def _dedupe_articles(articles: Iterable[NormalizedArticle]) -> List[NormalizedArticle]:
    unique: List[NormalizedArticle] = []
    seen = set()
    for article in articles:
        url_key = normalize_url(article.source_url)
        hash_key = compute_content_hash(article.title, article.content)
        key = f"{url_key}:{hash_key}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(article)
    return unique


def _filter_by_time_window(articles: Iterable[NormalizedArticle], hours: int) -> List[NormalizedArticle]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return [article for article in articles if article.published_at >= cutoff]


def _sort_articles(articles: Iterable[NormalizedArticle]) -> List[NormalizedArticle]:
    return sorted(articles, key=lambda a: a.published_at, reverse=True)


async def fetch_live_news(req: FeedRequest) -> NewsFeedResponse:
    sources = req.sources or DEFAULT_SOURCES
    tasks = []
    for source in sources:
        if source == "newsapi":
            tasks.append(fetch_newsapi(req))
        elif source == "yahoo_rss":
            tasks.append(fetch_yahoo_rss(req))
        elif source == "google_news_rss":
            tasks.append(fetch_google_news_rss(req))

    results = await asyncio.gather(*tasks, return_exceptions=True) if tasks else []
    articles = [article for batch in results if isinstance(batch, list) for article in batch]

    articles = _filter_by_time_window(articles, req.time_window_hours)
    articles = _dedupe_articles(articles)
    articles = _sort_articles(articles)[: req.limit]

    if req.analysis_mode != "none" and articles:
        semaphore = asyncio.Semaphore(ANALYSIS_CONCURRENCY)
        analysis_tasks = [
            _analyze_article(
                article,
                req.analysis_mode,
                semaphore,
                article.tickers[0] if article.tickers else None,
                req.explanation_detail,
                req.explanation_format,
            )
            for article in articles
        ]
        analysis_results = await asyncio.gather(*analysis_tasks)
    else:
        analysis_results = [
            {
                "sentiment_label": None,
                "sentiment_score": None,
                "impact_level": None,
                "impact_score": None,
                "ai_explanation": None,
                "ai_explanation_is_fallback": None,
            }
            for _ in articles
        ]

    response_articles = []
    for article, analysis in zip(articles, analysis_results):
        response_articles.append(
            NewsArticleOut(
                id=article.id,
                title=article.title,
                source_name=article.source_name,
                source_url=article.source_url,
                published_at=article.published_at,
                summary=article.summary,
                image_url=article.image_url,
                tickers=article.tickers,
                sentiment_label=analysis["sentiment_label"],
                sentiment_score=analysis["sentiment_score"],
                impact_level=analysis["impact_level"],
                impact_score=analysis["impact_score"],
                ai_explanation=analysis["ai_explanation"],
                ai_explanation_is_fallback=analysis["ai_explanation_is_fallback"],
            )
        )

    return NewsFeedResponse(articles=response_articles, count=len(response_articles))


async def analyze_text(req: AnalyzeRequest) -> AnalyzeResponse:
    if req.analysis_mode == "none":
        return AnalyzeResponse()

    text = f"{req.title}. {req.content}"
    sentiment = await classify_sentiment(text)
    impact_score, impact_level = await compute_impact_score(
        sentiment_score=sentiment["score"],
        title=req.title,
        is_primary=True,
        source_credibility=0.5,
    )
    explanation = None
    explanation_is_fallback = None
    if req.analysis_mode == "full":
        explanation, explanation_is_fallback = await generate_explanation(
            req.title,
            req.content,
            req.ticker or "MARKET",
            sentiment["label"],
            detail=req.explanation_detail,
            format_style=req.explanation_format,
        )

    return AnalyzeResponse(
        sentiment_label=sentiment["label"],
        sentiment_score=sentiment["score"],
        impact_level=impact_level,
        impact_score=impact_score,
        ai_explanation=explanation,
        ai_explanation_is_fallback=explanation_is_fallback,
    )
