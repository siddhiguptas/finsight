import pytest
from datetime import datetime

def test_impact_boundaries():
    from app.processing.sentiment_engine import compute_impact_score

    score, level = compute_impact_score(0.9, 0.92, True, datetime.utcnow(), "Apple earnings beat")
    assert level == "HIGH"
    assert score >= 0.8

    score, level = compute_impact_score(0.52, 0.35, False, datetime.utcnow(), "AAPL looking bullish")
    assert level == "LOW"

def test_impact_medium_range():
    from app.processing.sentiment_engine import compute_impact_score

    score, level = compute_impact_score(0.6, 0.5, False, datetime.utcnow(), "Some news")
    assert level == "MEDIUM"

def test_impact_with_earnings_keywords():
    from app.processing.sentiment_engine import compute_impact_score

    score, level = compute_impact_score(0.7, 0.6, True, datetime.utcnow(), "Q4 earnings report")
    assert level == "HIGH"
