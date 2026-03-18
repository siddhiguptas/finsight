import pytest
from app.services.filter_builder import NewsFilterBuilder

def test_add_impact_levels():
    builder = NewsFilterBuilder()
    builder.add_impact_levels(["HIGH", "MEDIUM"])

    where = builder.build_where()
    params = builder.get_params()

    assert "nsa.impact_level IN" in where
    assert len(params) == 2
    assert "HIGH" in params
    assert "MEDIUM" in params

def test_add_time_window():
    builder = NewsFilterBuilder()
    builder.add_time_window(24)

    where = builder.build_where()

    assert "na.published_at >= NOW() - INTERVAL '24 hours'" in where

def test_add_min_reliability():
    builder = NewsFilterBuilder()
    builder.add_min_reliability(0.7)

    where = builder.build_where()
    params = builder.get_params()

    assert "COALESCE" in where
    assert 0.7 in params

def test_add_tickers():
    builder = NewsFilterBuilder()
    builder.add_tickers(["AAPL", "MSFT"])

    where = builder.build_where()
    params = builder.get_params()

    assert "nst.ticker = ANY" in where
    assert params[0] == ["AAPL", "MSFT"]

def test_add_sentiments():
    builder = NewsFilterBuilder()
    builder.add_sentiments(["POSITIVE", "NEGATIVE"])

    where = builder.build_where()
    params = builder.get_params()

    assert "nsa.sentiment_label IN" in where
    assert len(params) == 2

def test_build_order_by_published_at_desc():
    builder = NewsFilterBuilder()
    order_by = builder.build_order_by("published_at", "desc")

    assert "na.published_at DESC" in order_by

def test_build_order_by_impact_score_asc():
    builder = NewsFilterBuilder()
    order_by = builder.build_order_by("impact_score", "asc")

    assert "nsa.impact_score ASC" in order_by

def test_build_where_base_conditions():
    builder = NewsFilterBuilder()
    where = builder.build_where()

    assert "na.is_deleted = FALSE" in where
    assert "na.is_duplicate = FALSE" in where

def test_filter_chaining():
    builder = NewsFilterBuilder()
    builder.add_impact_levels(["HIGH"]).add_time_window(24).add_min_reliability(0.5)

    where = builder.build_where()
    params = builder.get_params()

    assert "nsa.impact_level IN" in where
    assert "na.published_at >=" in where
    assert "COALESCE" in where
    assert len(params) == 3
