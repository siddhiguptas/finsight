import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    external_id: Mapped[str | None] = mapped_column(String(512), unique=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    full_text_ref: Mapped[str | None] = mapped_column(String(36))
    author: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    language: Mapped[str | None] = mapped_column(String(5), server_default=text("'en'"))
    image_url: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_credibility_score: Mapped[float | None] = mapped_column(
        Float, server_default=text("0.5")
    )
    is_duplicate: Mapped[bool | None] = mapped_column(Boolean, server_default=text("FALSE"))
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("news_articles.id")
    )
    is_deleted: Mapped[bool | None] = mapped_column(Boolean, server_default=text("FALSE"))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    __table_args__ = (
        Index("idx_news_published_at", text("published_at DESC")),
        Index("idx_news_source", "source_name"),
        Index("idx_news_content_hash", "content_hash"),
    )


class NewsStockTag(Base):
    __tablename__ = "news_stock_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool | None] = mapped_column(Boolean, server_default=text("FALSE"))
    mention_count: Mapped[int | None] = mapped_column(Integer, server_default=text("1"))
    tagged_by: Mapped[str | None] = mapped_column(String(50), server_default=text("'nlp'"))
    confidence: Mapped[float | None] = mapped_column(Float, server_default=text("1.0"))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    __table_args__ = (
        Index("idx_nst_ticker", "ticker"),
        Index("idx_nst_article", "article_id"),
        Index("idx_nst_ticker_created", "ticker", text("created_at DESC")),
    )


class NewsSectorTag(Base):
    __tablename__ = "news_sector_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False
    )
    sector_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sector_code: Mapped[str | None] = mapped_column(String(20))
    is_primary: Mapped[bool | None] = mapped_column(Boolean, server_default=text("FALSE"))
    confidence: Mapped[float | None] = mapped_column(Float, server_default=text("1.0"))
    tagged_by: Mapped[str | None] = mapped_column(String(50), server_default=text("'nlp'"))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    __table_args__ = (
        Index("idx_nsect_sector", "sector_name"),
        Index("idx_nsect_article", "article_id"),
    )


class NewsSentimentAnalysis(Base):
    __tablename__ = "news_sentiment_analysis"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False
    )
    ticker: Mapped[str | None] = mapped_column(String(10))
    sentiment_label: Mapped[str] = mapped_column(String(10), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    positive_score: Mapped[float | None] = mapped_column(Float)
    neutral_score: Mapped[float | None] = mapped_column(Float)
    negative_score: Mapped[float | None] = mapped_column(Float)
    impact_level: Mapped[str] = mapped_column(String(10), nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False)
    ai_explanation: Mapped[str | None] = mapped_column(Text)
    ai_model_used: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    __table_args__ = (
        Index("idx_nsa_article", "article_id"),
        Index("idx_nsa_ticker", "ticker"),
        Index("idx_nsa_sentiment", "sentiment_label", "impact_level"),
    )


class NewsReliabilityScore(Base):
    __tablename__ = "news_reliability_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sentiment_analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("news_sentiment_analysis.id"), nullable=False
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("news_articles.id"), nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    sentiment_predicted: Mapped[str] = mapped_column(String(10), nullable=False)
    price_at_publish: Mapped[float | None] = mapped_column(Float)
    price_24h_later: Mapped[float | None] = mapped_column(Float)
    price_72h_later: Mapped[float | None] = mapped_column(Float)
    actual_movement_24h: Mapped[float | None] = mapped_column(Float)
    actual_movement_72h: Mapped[float | None] = mapped_column(Float)
    movement_direction_24h: Mapped[str | None] = mapped_column(String(10))
    movement_direction_72h: Mapped[str | None] = mapped_column(String(10))
    prediction_correct_24h: Mapped[bool | None] = mapped_column(Boolean)
    prediction_correct_72h: Mapped[bool | None] = mapped_column(Boolean)
    reliability_score: Mapped[float | None] = mapped_column(Float)
    backtested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    __table_args__ = (
        Index("idx_nrs_ticker", "ticker"),
        Index("idx_nrs_article", "article_id"),
    )


class SourceReliabilityStats(Base):
    __tablename__ = "source_reliability_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    source_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    total_articles: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    correct_24h: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    correct_72h: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    accuracy_24h: Mapped[float | None] = mapped_column(Float, server_default=text("0.5"))
    accuracy_72h: Mapped[float | None] = mapped_column(Float, server_default=text("0.5"))
    avg_impact_score: Mapped[float | None] = mapped_column(Float, server_default=text("0.0"))
    last_updated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )


class ModelReliabilityStats(Base):
    __tablename__ = "model_reliability_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    model_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    total_predictions: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    correct_24h: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    correct_72h: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    accuracy_24h: Mapped[float | None] = mapped_column(Float, server_default=text("0.5"))
    accuracy_72h: Mapped[float | None] = mapped_column(Float, server_default=text("0.5"))
    last_updated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )


class UserNewsInteraction(Base):
    __tablename__ = "user_news_interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("news_articles.id"), nullable=False
    )
    interaction: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    __table_args__ = (
        UniqueConstraint("user_id", "article_id", "interaction", name="uq_user_article_interaction"),
        Index("idx_uni_user", "user_id", text("created_at DESC")),
    )
class UserWatchlist(Base):
    __tablename__ = "user_watchlist"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_user_ticker_watchlist"),
        Index("idx_uw_user", "user_id"),
    )


class TickerSectorMap(Base):
    __tablename__ = "ticker_sector_map"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100))
    market_cap_tier: Mapped[str | None] = mapped_column(String(10))
    exchange: Mapped[str | None] = mapped_column(String(20))
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )


class IngestionJobLog(Base):
    __tablename__ = "ingestion_job_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    job_name: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    articles_fetched: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    articles_new: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    articles_failed: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    status: Mapped[str | None] = mapped_column(String(20))
    error_message: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(String(255))


class HistoricalPrice(Base):
    __tablename__ = "historical_prices"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float | None] = mapped_column(Float)
    adj_close: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (Index("idx_historical_prices_ticker_date", "ticker", "date"),)
