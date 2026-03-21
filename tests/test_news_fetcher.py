import asyncio
from datetime import datetime, timedelta, timezone

from app.models.live_models import AnalyzeRequest
from app.services import news_fetcher
from app.services.news_fetcher import NormalizedArticle, normalize_url, compute_content_hash


def test_normalize_url():
    assert normalize_url("HTTPS://Example.com/Path/") == "example.com/path"


def test_deduplicate_articles():
    now = datetime.now(timezone.utc)
    art1 = NormalizedArticle(
        id="1",
        title="AAPL earnings",
        source_name="Test",
        source_url="https://example.com/a",
        published_at=now,
        summary="",
        image_url=None,
        content="Apple earnings beat",
        tickers=["AAPL"],
    )
    art2 = NormalizedArticle(
        id="2",
        title="AAPL earnings",
        source_name="Test",
        source_url="https://example.com/a",
        published_at=now,
        summary="",
        image_url=None,
        content="Apple earnings beat",
        tickers=["AAPL"],
    )
    deduped = news_fetcher._dedupe_articles([art1, art2])
    assert len(deduped) == 1


def test_time_window_filter():
    now = datetime.now(timezone.utc)
    recent = NormalizedArticle(
        id="recent",
        title="Recent",
        source_name="Test",
        source_url="https://example.com/recent",
        published_at=now - timedelta(hours=2),
        summary="",
        image_url=None,
        content="",
        tickers=["AAPL"],
    )
    old = NormalizedArticle(
        id="old",
        title="Old",
        source_name="Test",
        source_url="https://example.com/old",
        published_at=now - timedelta(hours=48),
        summary="",
        image_url=None,
        content="",
        tickers=["AAPL"],
    )
    filtered = news_fetcher._filter_by_time_window([recent, old], 24)
    assert [a.id for a in filtered] == ["recent"]


def test_analyze_text_none_mode(monkeypatch):
    async def boom(_text):
        raise AssertionError("classify_sentiment should not be called in none mode")

    monkeypatch.setattr(news_fetcher, "classify_sentiment", boom)
    req = AnalyzeRequest(title="t", content="c", analysis_mode="none")
    result = asyncio.run(news_fetcher.analyze_text(req))
    assert result.sentiment_label is None
    assert result.impact_score is None


def test_analyze_text_fast_mode(monkeypatch):
    async def fake_sentiment(_text):
        return {"label": "POSITIVE", "score": 0.9}

    async def fake_impact(**_kwargs):
        return 0.7, "HIGH"

    async def fake_expl(*_args, **_kwargs):
        return "explanation"

    monkeypatch.setattr(news_fetcher, "classify_sentiment", fake_sentiment)
    monkeypatch.setattr(news_fetcher, "compute_impact_score", fake_impact)
    monkeypatch.setattr(news_fetcher, "generate_explanation", fake_expl)

    req = AnalyzeRequest(title="t", content="c", analysis_mode="fast")
    result = asyncio.run(news_fetcher.analyze_text(req))
    assert result.sentiment_label == "POSITIVE"
    assert result.impact_level == "HIGH"
    assert result.ai_explanation is None


def test_content_hash_consistency():
    h1 = compute_content_hash("Apple", "Earnings beat expectations")
    h2 = compute_content_hash("Apple", "Earnings beat expectations")
    assert h1 == h2
