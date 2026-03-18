# FinSight — Intelligent News Aggregation & Analysis System
## Complete Implementation Plan (Zero → Production)

**Module Owner:** Siddhi (Data Engineering & News Aggregation)  
**Project:** FinSight — Financial Insights Platform  
**Document Version:** 1.0 | **Date:** March 2026  
**Standard:** Institutional-grade, Bloomberg/AlphaSense-class pipeline

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Tech Stack](#2-tech-stack)
3. [Complete Database Schema (A-to-Z)](#3-complete-database-schema-a-to-z)
4. [Data Flow Diagrams](#4-data-flow-diagrams)
5. [Phase 1 — Research & Dataset Collection](#phase-1--research--dataset-collection)
6. [Phase 2 — Data Ingestion Pipeline](#phase-2--data-ingestion-pipeline)
7. [Phase 3 — NLP Processing Pipeline](#phase-3--nlp-processing-pipeline)
8. [Phase 4 — Sentiment & Impact Engine](#phase-4--sentiment--impact-engine)
9. [Phase 5 — Reliability Scoring System](#phase-5--reliability-scoring-system)

> **Continued in:** [`implementationplan_part2.md`](./implementationplan_part2.md) — Phases 6–10, API Design, Filtering, Testing, Deployment, Cost & Scalability

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NEWS SOURCES LAYER                           │
│  [NewsAPI] [Alpha Vantage] [RSS Feeds] [Web Scrapers] [Reddit API]  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ Raw Articles (JSON/HTML)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INGESTION & QUEUE LAYER                           │
│         Celery Beat (scheduled) + BullMQ / Redis Streams            │
│         Deduplication Engine → Normalization → Queue                │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ Deduplicated, normalized article events
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     NLP PROCESSING PIPELINE                          │
│   Entity Extraction (spaCy) → Categorization → Stock Ticker Tagging │
│   → Sector Mapping → Relevance Scoring                              │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ Enriched article objects
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  SENTIMENT & IMPACT ENGINE                           │
│   FinBERT Sentiment → Gemini LLM Explanation → Impact Score         │
│   → Category Assignment (Portfolio / Sector / General)              │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ Analyzed news records
                            ▼
┌──────────────────┬────────────────────┬────────────────────────────┐
│   PostgreSQL     │   Redis Cache       │   MongoDB (raw articles)   │
│  (structured)    │  (hot news feed)    │   (unstructured text)      │
└──────────────────┴────────────────────┴────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RELIABILITY SCORING ENGINE                        │
│  Nightly Batch: Compare yesterday's sentiments vs actual price Δ    │
│  → Update reliability_score per article/source/model                │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│               BACKEND API LAYER (FastAPI / Django REST)             │
│   /news/feed  /news/filter  /news/article/:id  /news/reliability    │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│               FRONTEND (React + Siddhi's Dashboard)                  │
│   Filtered News Feed | AI Explanation Cards | Reliability Badges     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Real-Time vs Batch Strategy

| Concern | Strategy | Frequency |
|---|---|---|
| Breaking news ingestion | Polling NewsAPI/Alpha Vantage | Every 5 minutes |
| RSS feed scraping | Celery Beat scheduled task | Every 10 minutes |
| Sentiment analysis | Async task after ingestion | Within 2 min of ingestion |
| LLM explanation generation | Queued async task (Celery) | Within 5 min of ingestion |
| Reliability score recalculation | Nightly batch job | 11 PM UTC daily |
| Stock price correlation fetch | Nightly batch job | 11:30 PM UTC daily |
| Cache invalidation | TTL-based + event-driven | Per article update |
| Sector/market-level aggregation | Hourly batch | Every 60 minutes |

---

## 2. Tech Stack

### 2.1 Core Backend
| Layer | Technology | Justification |
|---|---|---|
| API Framework | **FastAPI** (Python 3.11) | Async, high-perf, OpenAPI auto-docs |
| Task Queue | **Celery 5** + **Redis** broker | Distributed async tasks, retries, beat scheduler |
| ML/NLP | **spaCy 3.7**, **FinBERT** (HuggingFace), **Google Gemini API** | FinBERT = finance-specific; Gemini = explanations |
| Embeddings | **sentence-transformers** (`all-MiniLM-L6-v2`) | Deduplication & semantic similarity |
| Primary DB | **PostgreSQL 15** (via SQLAlchemy + Alembic) | ACID, relational joins, partitioning |
| Document Store | **MongoDB 7** | Raw article text, flexible schema |
| Cache | **Redis 7** | Hot feed cache, rate-limit counters |
| HTTP Client | **httpx** (async) + **BeautifulSoup4** + **Playwright** | API calls + scraping + JS-heavy pages |
| Validation | **Pydantic v2** | Request/response models |
| Auth Integration | JWT (shared with Pratyaksha's auth module) | Session-based user identification |

### 2.2 News Sources & APIs

| Source | Type | Data Coverage | Cost | Rate Limit |
|---|---|---|---|---|
| **NewsAPI.org** | REST API | 150k+ sources, global news | Free: 100req/day; Paid: $449/mo | 100/day (free), 500/hr (paid) |
| **Alpha Vantage News** | REST API | Market news + sentiment pre-scored | Free: 25req/day; Premium: $50/mo | 5/min (free) |
| **Yahoo Finance RSS** | RSS/Scraping | Stock-specific news, earnings | Free | Polite crawl |
| **Google News RSS** | RSS | General news, broad coverage | Free | Polite crawl |
| **Reddit (PRAW)** | PRAW API (Python) | r/investing, r/stocks, r/wallstreetbets | Free | 60req/min OAuth |
| **SEC EDGAR RSS** | RSS/API | Official filings, earnings | Free | 10req/sec |
| **Reuters/AP Wires** | RSS Scraping | High-credibility news | Free (RSS) | Polite crawl |
| **Seeking Alpha** | Scraping (fallback) | Deep stock analysis | Conditional | Polite crawl |

### 2.3 Infrastructure
| Component | Technology |
|---|---|
| Containerization | Docker + Docker Compose |
| Deployment | Railway / Render (dev) → AWS ECS (prod) |
| Monitoring | Sentry (errors) + Prometheus + Grafana |
| Secrets | python-dotenv + AWS Secrets Manager (prod) |
| CI/CD | GitHub Actions |

---

## 3. Complete Database Schema (A-to-Z)

> Every table, every column, every relationship — what gets stored, why, and when.

### 3.1 PostgreSQL Schema

#### Table: `news_articles`
*Central table. One row per unique processed article.*

```sql
CREATE TABLE news_articles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id         VARCHAR(512) UNIQUE,          -- Source's own article ID or URL hash
    source_name         VARCHAR(255) NOT NULL,         -- "Reuters", "NewsAPI", "Yahoo Finance"
    source_url          TEXT NOT NULL,                 -- Full canonical URL
    title               TEXT NOT NULL,                 -- Article headline
    summary             TEXT,                          -- First 500 chars or API-provided summary
    full_text_ref       VARCHAR(36),                   -- MongoDB ObjectId → raw full text
    author              VARCHAR(255),
    published_at        TIMESTAMPTZ NOT NULL,          -- Original publication time (UTC)
    ingested_at         TIMESTAMPTZ DEFAULT NOW(),     -- When WE fetched it
    processed_at        TIMESTAMPTZ,                   -- When NLP pipeline finished
    language            CHAR(5) DEFAULT 'en',
    image_url           TEXT,
    content_hash        CHAR(64) UNIQUE NOT NULL,      -- SHA-256 of normalized title+body for dedup
    source_credibility_score FLOAT DEFAULT 0.5,       -- Pre-assigned per source (0.0–1.0)
    is_duplicate        BOOLEAN DEFAULT FALSE,
    duplicate_of        UUID REFERENCES news_articles(id),
    is_deleted          BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_news_published_at ON news_articles(published_at DESC);
CREATE INDEX idx_news_source ON news_articles(source_name);
CREATE INDEX idx_news_content_hash ON news_articles(content_hash);
```

**What gets stored here:** Every article we fetch, after deduplication. Raw text goes to MongoDB (referenced by `full_text_ref`). This is the master record.

---

#### Table: `news_stock_tags`
*Many-to-many: which stocks does this article mention/affect?*

```sql
CREATE TABLE news_stock_tags (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id  UUID NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    ticker      VARCHAR(10) NOT NULL,                 -- "AAPL", "MSFT", "TSLA"
    company_name VARCHAR(255),
    is_primary  BOOLEAN DEFAULT FALSE,                -- TRUE = article is primarily about this stock
    mention_count INT DEFAULT 1,                      -- How many times ticker appears in text
    tagged_by   VARCHAR(50) DEFAULT 'nlp',            -- 'nlp' | 'api' | 'manual'
    confidence  FLOAT DEFAULT 1.0,                    -- NER confidence score (0.0–1.0)
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nst_ticker ON news_stock_tags(ticker);
CREATE INDEX idx_nst_article ON news_stock_tags(article_id);
CREATE INDEX idx_nst_ticker_created ON news_stock_tags(ticker, created_at DESC);
```

**What gets stored here:** Every ticker mentioned in the article. `is_primary=TRUE` means the article is fundamentally about that stock (e.g., "Apple reports record earnings" → AAPL is primary). Used to build the Portfolio News feed.

---

#### Table: `news_sector_tags`
*Which sectors does this article relate to?*

```sql
CREATE TABLE news_sector_tags (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id  UUID NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    sector_name VARCHAR(100) NOT NULL,                -- "Technology", "Healthcare", "Energy"
    sector_code VARCHAR(20),                          -- GICS code e.g. "45" for IT
    is_primary  BOOLEAN DEFAULT FALSE,
    confidence  FLOAT DEFAULT 1.0,
    tagged_by   VARCHAR(50) DEFAULT 'nlp',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nsect_sector ON news_sector_tags(sector_name);
CREATE INDEX idx_nsect_article ON news_sector_tags(article_id);
```

**What gets stored here:** Sector assignments derived from the stock tickers in the article (ticker → sector via a lookup table) or from keyword-based NLP classification. Used for Sector News feed.

---

#### Table: `news_sentiment_analysis`
*One row per article per ticker (primary ticker gets its own sentiment analysis).*

```sql
CREATE TABLE news_sentiment_analysis (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id          UUID NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    ticker              VARCHAR(10),                  -- NULL = general market sentiment
    sentiment_label     VARCHAR(10) NOT NULL,         -- 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE'
    sentiment_score     FLOAT NOT NULL,               -- Confidence of label (0.0–1.0)
    positive_score      FLOAT,                        -- Raw FinBERT positive logit
    neutral_score       FLOAT,                        -- Raw FinBERT neutral logit
    negative_score      FLOAT,                        -- Raw FinBERT negative logit
    impact_level        VARCHAR(10) NOT NULL,         -- 'HIGH' | 'MEDIUM' | 'LOW'
    impact_score        FLOAT NOT NULL,               -- 0.0–1.0, computed (see §4)
    ai_explanation      TEXT,                         -- Gemini-generated explanation
    ai_model_used       VARCHAR(100),                 -- "gemini-1.5-flash" | "finbert-v1"
    prompt_version      VARCHAR(20),                  -- Track prompt changes for A/B testing
    analyzed_at         TIMESTAMPTZ DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nsa_article ON news_sentiment_analysis(article_id);
CREATE INDEX idx_nsa_ticker ON news_sentiment_analysis(ticker);
CREATE INDEX idx_nsa_sentiment ON news_sentiment_analysis(sentiment_label, impact_level);
```

**What gets stored here:** The AI's verdict on each article. One row for general sentiment + one row per primary ticker if article covers multiple stocks. The `ai_explanation` field is the human-readable paragraph shown in the UI.

---

#### Table: `news_reliability_scores`
*Tracks per-article prediction accuracy after price movement is known.*

```sql
CREATE TABLE news_reliability_scores (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sentiment_analysis_id   UUID NOT NULL REFERENCES news_sentiment_analysis(id),
    article_id              UUID NOT NULL REFERENCES news_articles(id),
    ticker                  VARCHAR(10) NOT NULL,
    sentiment_predicted     VARCHAR(10) NOT NULL,     -- What we predicted: 'POSITIVE' etc.
    price_at_publish        FLOAT,                    -- Stock price at article publish time
    price_24h_later         FLOAT,                    -- Stock price 24h after publish
    price_72h_later         FLOAT,                    -- Stock price 72h after publish
    actual_movement_24h     FLOAT,                    -- % change: (24h - publish) / publish * 100
    actual_movement_72h     FLOAT,
    movement_direction_24h  VARCHAR(10),              -- 'UP' | 'DOWN' | 'FLAT' (±0.5% threshold)
    movement_direction_72h  VARCHAR(10),
    prediction_correct_24h  BOOLEAN,                  -- Did sentiment match direction at 24h?
    prediction_correct_72h  BOOLEAN,
    reliability_score       FLOAT,                    -- Final computed score for THIS article (0–1)
    backtested_at           TIMESTAMPTZ,              -- When this row was computed
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nrs_ticker ON news_reliability_scores(ticker);
CREATE INDEX idx_nrs_article ON news_reliability_scores(article_id);
```

**What gets stored here:** The ground-truth outcome for every prediction. Populated by the nightly batch job that fetches historical prices and compares them against our sentiment predictions.

---

#### Table: `source_reliability_stats`
*Aggregate reliability per news source (computed from above).*

```sql
CREATE TABLE source_reliability_stats (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name     VARCHAR(255) UNIQUE NOT NULL,
    total_articles  INT DEFAULT 0,
    correct_24h     INT DEFAULT 0,                    -- Count of correct 24h predictions
    correct_72h     INT DEFAULT 0,
    accuracy_24h    FLOAT DEFAULT 0.5,                -- correct_24h / total_articles
    accuracy_72h    FLOAT DEFAULT 0.5,
    avg_impact_score FLOAT DEFAULT 0.0,
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);
```

---

#### Table: `model_reliability_stats`
*Tracks reliability per model version (FinBERT vs Gemini vs hybrid).*

```sql
CREATE TABLE model_reliability_stats (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name      VARCHAR(100) UNIQUE NOT NULL,     -- "finbert-v1", "gemini-1.5-flash"
    prompt_version  VARCHAR(20),
    total_predictions INT DEFAULT 0,
    correct_24h     INT DEFAULT 0,
    correct_72h     INT DEFAULT 0,
    accuracy_24h    FLOAT DEFAULT 0.5,
    accuracy_72h    FLOAT DEFAULT 0.5,
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);
```

---

#### Table: `user_news_interactions`
*Tracks which articles each user has seen, saved, or dismissed (for personalization).*

```sql
CREATE TABLE user_news_interactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,                    -- FK to users table (Pratyaksha's module)
    article_id      UUID NOT NULL REFERENCES news_articles(id),
    interaction     VARCHAR(20) NOT NULL,             -- 'viewed' | 'saved' | 'dismissed' | 'shared'
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, article_id, interaction)
);

CREATE INDEX idx_uni_user ON user_news_interactions(user_id, created_at DESC);
```

---

#### Table: `ticker_sector_map`
*Static lookup: stock ticker → sector (populated once, updated quarterly).*

```sql
CREATE TABLE ticker_sector_map (
    ticker          VARCHAR(10) PRIMARY KEY,
    company_name    VARCHAR(255) NOT NULL,
    sector          VARCHAR(100) NOT NULL,            -- GICS sector name
    industry        VARCHAR(100),                     -- GICS industry
    market_cap_tier VARCHAR(10),                      -- 'LARGE' | 'MID' | 'SMALL'
    exchange        VARCHAR(20),                      -- 'NYSE' | 'NASDAQ'
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

#### Table: `ingestion_job_log`
*Audit trail for every ingestion run.*

```sql
CREATE TABLE ingestion_job_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name        VARCHAR(100) NOT NULL,            -- "newsapi_poll", "yahoo_rss_scrape"
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    articles_fetched INT DEFAULT 0,
    articles_new    INT DEFAULT 0,                    -- After dedup
    articles_failed INT DEFAULT 0,
    status          VARCHAR(20),                      -- 'RUNNING' | 'SUCCESS' | 'FAILED'
    error_message   TEXT,
    source_name     VARCHAR(255)
);
```

---

### 3.2 MongoDB Collection: `raw_articles`
*Stores the full, unstructured text of each article.*

```json
{
  "_id": "ObjectId",
  "postgres_id": "UUID string — links to news_articles.id",
  "source": "Reuters",
  "url": "https://...",
  "title": "Apple Beats Q4 Earnings Expectations",
  "full_text": "Apple Inc. reported quarterly earnings that...[full body]",
  "html_snapshot": "<html>...",
  "meta_keywords": ["Apple", "AAPL", "earnings", "Q4"],
  "word_count": 842,
  "scraped_at": "ISODate",
  "nlp_entities": [
    { "text": "Apple", "label": "ORG", "start": 0, "end": 5 },
    { "text": "AAPL", "label": "TICKER", "start": 10, "end": 14 }
  ],
  "key_sentences": [
    "Apple reported $1.29 EPS, beating estimates of $1.18.",
    "Revenue grew 8% YoY to $94.9B."
  ]
}
```

**What gets stored here:** Everything raw — full HTML, full text, extracted entities, key sentences (used as input to Gemini for explanation generation). Kept for auditability and reprocessing.

---

### 3.3 Redis Cache Keys

| Key Pattern | Value | TTL | Purpose |
|---|---|---|---|
| `feed:user:{user_id}:portfolio` | JSON array of article IDs | 5 min | User's portfolio news feed |
| `feed:user:{user_id}:sector` | JSON array of article IDs | 10 min | User's sector news feed |
| `feed:general:market` | JSON array of article IDs | 15 min | General market news |
| `article:{article_id}` | Full enriched article JSON | 30 min | Per-article detail cache |
| `reliability:source:{source}` | Float score | 1 hour | Source reliability cache |
| `reliability:ticker:{ticker}` | Float score | 1 hour | Ticker-level avg reliability |
| `rate_limit:newsapi` | Request count | 60 sec window | API rate limit counter |
| `dedup:hash:{content_hash}` | "1" | 48 hours | Deduplication bloom-filter substitute |

---

## 4. Data Flow Diagrams

### 4.1 Article Ingestion → Storage Flow

```
[Source API / RSS]
       │
       ▼
[Fetch Raw Article]
       │
       ├─► [Compute content_hash = SHA256(normalize(title + body[:200]))]
       │
       ├─► [Check Redis: dedup:hash:{hash} EXISTS?]
       │         │
       │    YES──┘──► [Discard. Log as duplicate. END.]
       │    NO
       │         │
       ├─► [Check PostgreSQL: content_hash UNIQUE constraint]
       │         │
       │    EXISTS ► [Mark is_duplicate=TRUE. END.]
       │    NEW
       │         │
       ├─► [Store full text → MongoDB raw_articles collection]
       │         │
       │    returns mongo_id
       │         │
       ├─► [Store metadata → PostgreSQL news_articles (full_text_ref=mongo_id)]
       │         │
       │    returns postgres_uuid
       │         │
       ├─► [Set Redis key: dedup:hash:{hash} = "1" TTL=48h]
       │
       └─► [Push event to Celery Queue: {task: "process_article", id: postgres_uuid}]
```

### 4.2 NLP → Sentiment → Storage Flow

```
[Celery Worker picks up process_article task]
       │
       ▼
[Fetch article from MongoDB by full_text_ref]
       │
       ▼
[spaCy NLP Pipeline]
    ├── NER: Extract ORG, PERSON, GPE, MONEY entities
    ├── Ticker extraction: regex + FinancialNER model
    ├── Keyword extraction: TF-IDF top-10 terms
    └── Key sentence extraction: TextRank (top 3 sentences)
       │
       ▼
[Ticker → Sector Mapping via ticker_sector_map table]
       │
       ▼
[INSERT news_stock_tags rows]
[INSERT news_sector_tags rows]
[UPDATE MongoDB nlp_entities, key_sentences fields]
       │
       ▼
[FinBERT Sentiment Analysis on key_sentences joined text]
    → Returns: {positive: 0.82, neutral: 0.12, negative: 0.06}
    → Label: POSITIVE, Score: 0.82
       │
       ▼
[Impact Score Calculation (see §4 Algorithm)]
    → Returns: impact_score=0.74, impact_level='HIGH'
       │
       ▼
[Gemini LLM Explanation Generation]
    → Input: title + key_sentences + sentiment + ticker
    → Output: 2–3 sentence explanation
       │
       ▼
[INSERT news_sentiment_analysis row]
       │
       ▼
[Invalidate Redis cache keys for affected tickers/sectors]
       │
       ▼
[Update ingestion_job_log]
```

---

## Phase 1 — Research & Dataset Collection

**Goal:** Identify all data sources, collect training/validation datasets, map ticker universe.

### Tasks

**1.1 Define Ticker Universe**
- Source top 500 US stocks (S&P 500) + any stocks in user portfolios.
- Populate `ticker_sector_map` table from Yahoo Finance API or a static CSV (GICS sectors).
- Script: `python scripts/populate_ticker_map.py --source sp500`
- Store: `ticker_sector_map` PostgreSQL table (≈500 initial rows, grows with user portfolios).

**1.2 Collect Historical News Dataset for Training/Backtesting**
- NewsAPI `/everything` endpoint for past 30 days across all 500 tickers.
- Combine with the `FinancialPhraseBank` dataset (Malo et al., 2014) — 4,846 sentences annotated Positive/Neutral/Negative → for FinBERT fine-tuning validation.
- Collect from `news-headlines` Kaggle dataset (CNBC, Reuters, Guardian headlines 2017-2023).
- **Store:** CSV files in `data/raw/` → MongoDB `training_articles` collection.

**1.3 Collect Historical Price Data**
- Fetch daily OHLCV for all 500 tickers from **Alpha Vantage** (`TIME_SERIES_DAILY_ADJUSTED`) for past 5 years.
- **Store:** PostgreSQL table `historical_prices(ticker, date, open, high, low, close, adj_close, volume)`.
- Used later by reliability scoring nightly batch.

**1.4 Source Credibility Pre-Scoring**
- Manually assign initial `source_credibility_score` to known sources:
  - Reuters, AP, Bloomberg Wire: 0.92
  - Yahoo Finance, CNBC, MarketWatch: 0.78
  - SeekingAlpha (user articles): 0.60
  - Reddit posts: 0.35
  - Unknown scraped sources: 0.40
- Store in `source_reliability_stats.accuracy_24h` as starting prior.

**Tools:** `pandas`, `requests`, `yfinance`, Alpha Vantage API, NewsAPI free tier  
**Expected Outputs:** 
- `ticker_sector_map` table populated (500+ rows)
- `historical_prices` table populated (5 years × 500 stocks = 650k rows)
- `data/raw/training_corpus.csv` (≥10,000 labeled sentences)  
**Dependencies:** PostgreSQL running, MongoDB running, API keys configured in `.env`

---

## Phase 2 — Data Ingestion Pipeline

**Goal:** Build a robust, scheduled, multi-source ingestion system with deduplication.

### Tasks

**2.1 Project Structure Setup**
```
finsight-news/
├── app/
│   ├── ingestion/
│   │   ├── newsapi_client.py
│   │   ├── rss_scraper.py
│   │   ├── yahoo_scraper.py
│   │   ├── reddit_client.py
│   │   └── sec_client.py
│   ├── processing/
│   │   ├── deduplicator.py
│   │   ├── normalizer.py
│   │   └── text_extractor.py
│   ├── models/ (SQLAlchemy ORM models)
│   ├── tasks/ (Celery tasks)
│   ├── api/ (FastAPI routers)
│   └── core/ (config, db connections)
├── celery_app.py
├── main.py
└── docker-compose.yml
```

**2.2 Celery Beat Schedule (celery_app.py)**
```python
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    'newsapi-poll': {
        'task': 'app.tasks.ingest.fetch_newsapi',
        'schedule': 300.0,  # every 5 minutes
    },
    'yahoo-rss-scrape': {
        'task': 'app.tasks.ingest.fetch_yahoo_rss',
        'schedule': 600.0,  # every 10 minutes
    },
    'reddit-poll': {
        'task': 'app.tasks.ingest.fetch_reddit',
        'schedule': 900.0,  # every 15 minutes
    },
    'reliability-batch': {
        'task': 'app.tasks.reliability.run_nightly_backtest',
        'schedule': crontab(hour=23, minute=0),  # 11 PM UTC
    },
}
```

**2.3 Deduplication Engine**
```python
# app/processing/deduplicator.py
import hashlib, re

def compute_content_hash(title: str, body: str) -> str:
    """Normalize and hash to detect near-duplicate articles."""
    normalized = re.sub(r'\s+', ' ', (title + body[:200]).lower().strip())
    normalized = re.sub(r'[^a-z0-9 ]', '', normalized)
    return hashlib.sha256(normalized.encode()).hexdigest()

async def is_duplicate(hash: str, redis_client, db) -> bool:
    # Step 1: Check Redis bloom-filter substitute (fast path, O(1))
    if await redis_client.get(f"dedup:hash:{hash}"):
        return True
    # Step 2: Check PostgreSQL unique constraint (slow path, fallback)
    result = await db.execute(
        "SELECT id FROM news_articles WHERE content_hash = $1 LIMIT 1", hash
    )
    return result is not None
```

**2.4 Rate Limit Handler**
```python
# app/ingestion/rate_limiter.py
class APIRateLimiter:
    def __init__(self, redis, key: str, max_calls: int, window_seconds: int):
        self.redis = redis
        self.key = f"rate_limit:{key}"
        self.max_calls = max_calls
        self.window = window_seconds

    async def acquire(self):
        count = await self.redis.incr(self.key)
        if count == 1:
            await self.redis.expire(self.key, self.window)
        if count > self.max_calls:
            wait = await self.redis.ttl(self.key)
            raise RateLimitExceeded(f"Rate limit hit. Retry in {wait}s")
```

**2.5 Web Scraping Fallback Strategy**
- **Primary:** Official API (NewsAPI, Alpha Vantage)
- **Fallback 1:** RSS feed parsing with `feedparser`
- **Fallback 2:** Direct HTML scraping with `httpx` + `BeautifulSoup4` via `newspaper3k`
- **Fallback 3:** Playwright headless browser for JS-rendered pages
- **Credibility flag:** Scraped content gets `source_credibility_score -= 0.1` vs API content

**2.6 Fake/Low-Credibility Filtering Rules**
```python
CREDIBILITY_RULES = [
    # Rule 1: Known low-quality domains blacklist
    lambda art: art.source_domain not in BLACKLISTED_DOMAINS,
    # Rule 2: Title clickbait detection (ALL CAPS ratio > 40%)
    lambda art: sum(1 for c in art.title if c.isupper()) / len(art.title) < 0.4,
    # Rule 3: Article too short (< 100 words = likely scrape error)
    lambda art: art.word_count >= 100,
    # Rule 4: Published in future (data error)
    lambda art: art.published_at <= datetime.utcnow(),
    # Rule 5: No ticker or sector association possible
    lambda art: len(art.detected_tickers) > 0 or art.category == 'GENERAL',
]
```

**Tools:** `celery[redis]`, `feedparser`, `httpx`, `newspaper3k`, `playwright`, `beautifulsoup4`  
**Expected Outputs:**
- Running Celery workers processing articles every 5 minutes
- Deduplication rate > 85% (per news cycle)
- `ingestion_job_log` filled after each run
- Articles flowing into PostgreSQL + MongoDB  
**Dependencies:** Phase 1 complete, Redis + PostgreSQL + MongoDB running, API keys in `.env`

---

## Phase 3 — NLP Processing Pipeline

**Goal:** Extract structured intelligence from raw article text.

### Tasks

**3.1 spaCy Pipeline Setup**
```python
# app/processing/nlp_pipeline.py
import spacy

nlp = spacy.load("en_core_web_lg")  # Large model for better NER

# Custom ticker pattern matcher
from spacy.matcher import Matcher
matcher = Matcher(nlp.vocab)
ticker_pattern = [{"TEXT": {"REGEX": r"^[A-Z]{1,5}$"}},
                  {"TEXT": {"IN": ["NYSE", "NASDAQ", "(", ")"]}, "OP": "?"}]
matcher.add("STOCK_TICKER", [ticker_pattern])
```

**3.2 Entity Extraction → Ticker Tagging**
```python
def extract_tickers_from_article(text: str, title: str) -> list[dict]:
    full_text = title + ". " + text
    doc = nlp(full_text)
    
    tickers = {}
    
    # Method 1: Regex pattern match (e.g., "AAPL", "(NASDAQ: TSLA)")
    for match in re.finditer(r'\b([A-Z]{1,5})\b', full_text):
        candidate = match.group(1)
        if candidate in KNOWN_TICKERS:  # Lookup against ticker_sector_map
            tickers[candidate] = tickers.get(candidate, 0) + 1
    
    # Method 2: Company name → ticker via lookup
    for ent in doc.ents:
        if ent.label_ == "ORG":
            ticker = COMPANY_TO_TICKER.get(ent.text.lower())
            if ticker:
                tickers[ticker] = tickers.get(ticker, 0) + 1
    
    # Determine primary ticker (highest mention count)
    return [
        {"ticker": k, "mention_count": v, "is_primary": (k == max(tickers, key=tickers.get))}
        for k, v in tickers.items()
    ]
```

**3.3 Key Sentence Extraction (TextRank)**
```python
from summa import summarize  # summa implements TextRank

def extract_key_sentences(text: str, ratio: float = 0.2) -> list[str]:
    """Extract top 20% sentences by TextRank importance score."""
    summary = summarize(text, ratio=ratio, split=True)
    return summary[:5]  # Cap at 5 key sentences for LLM input
```

**3.4 Three-Tier Category Assignment**
```python
def assign_news_category(article, user_portfolio_tickers, user_sector_subscriptions):
    """
    Returns: 'PORTFOLIO' | 'SECTOR' | 'GENERAL'
    Priority: PORTFOLIO > SECTOR > GENERAL
    """
    article_tickers = {tag.ticker for tag in article.stock_tags}
    article_sectors = {tag.sector_name for tag in article.sector_tags}
    
    if article_tickers & set(user_portfolio_tickers):
        return "PORTFOLIO"
    elif article_sectors & set(user_sector_subscriptions):
        return "SECTOR"
    else:
        return "GENERAL"
```

**3.5 Keyword-Based Sector Classification (Fallback)**
When a ticker can't be extracted, use keyword matching to determine sector:
```python
SECTOR_KEYWORDS = {
    "Technology":    ["software", "SaaS", "chip", "semiconductor", "AI", "cloud", "app"],
    "Healthcare":    ["FDA", "drug", "pharma", "clinical trial", "biotech", "hospital"],
    "Energy":        ["oil", "gas", "crude", "OPEC", "pipeline", "refinery", "LNG"],
    "Finance":       ["bank", "Fed", "interest rate", "mortgage", "insurance", "fintech"],
    "Consumer":      ["retail", "e-commerce", "consumer spending", "Amazon", "Walmart"],
}

def classify_sector_by_keywords(title: str, text: str) -> str | None:
    combined = (title + " " + text).lower()
    scores = {sector: sum(combined.count(kw.lower()) for kw in kws)
              for sector, kws in SECTOR_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 2 else None
```

**Tools:** `spacy`, `en_core_web_lg`, `summa`, `regex`, `nltk`  
**Expected Outputs:**
- Every ingested article has stock tags + sector tags in DB
- Category (PORTFOLIO/SECTOR/GENERAL) assigned per user context
- MongoDB updated with `nlp_entities` and `key_sentences`  
**Dependencies:** Phase 2 pipeline running, `ticker_sector_map` populated

---

## Phase 4 — Sentiment & Impact Engine

**Goal:** Classify sentiment using FinBERT, generate human-readable AI explanations using Gemini, and compute impact scores.

### Tasks

**4.1 FinBERT Sentiment Classification**
```python
from transformers import pipeline

finbert = pipeline(
    "text-classification",
    model="ProsusAI/finbert",           # Finance-specific BERT model
    tokenizer="ProsusAI/finbert",
    device=0,                           # GPU if available, else cpu=-1
    return_all_scores=True,
    max_length=512,
    truncation=True,
)

def classify_sentiment(key_sentences: list[str]) -> dict:
    """Run FinBERT on joined key sentences (max 512 tokens)."""
    input_text = " ".join(key_sentences)[:3000]  # Safe truncation before tokenizer
    results = finbert(input_text)[0]
    scores = {r['label'].upper(): r['score'] for r in results}
    label = max(scores, key=scores.get)
    return {
        "sentiment_label": label,
        "sentiment_score": scores[label],
        "positive_score": scores.get("POSITIVE", 0),
        "neutral_score": scores.get("NEUTRAL", 0),
        "negative_score": scores.get("NEGATIVE", 0),
    }
```

**4.2 Impact Score Algorithm**
```
impact_score = w1 × sentiment_strength
             + w2 × source_credibility
             + w3 × ticker_specificity
             + w4 × recency_factor
             + w5 × keyword_weight

Where:
  sentiment_strength  = |sentiment_score - 0.5| × 2  (0=neutral, 1=extreme)
  source_credibility  = source_credibility_score from source_reliability_stats
  ticker_specificity  = 1.0 if article is_primary=TRUE, 0.5 if mentioned only
  recency_factor      = exp(-λ × hours_since_publish), λ=0.05
  keyword_weight      = 1.0 if "earnings|guidance|merger|acquisition|lawsuit|FDA" in title else 0.6

Weights: w1=0.35, w2=0.25, w3=0.20, w4=0.12, w5=0.08

Impact Level Thresholds:
  HIGH:   impact_score >= 0.70
  MEDIUM: impact_score >= 0.40
  LOW:    impact_score < 0.40
```

```python
import math, re
from datetime import datetime, timezone

HIGH_IMPACT_KEYWORDS = re.compile(
    r'\b(earnings|guidance|merger|acquisition|FDA|bankruptcy|lawsuit|recall|'
    r'dividend|split|buyback|layoff|CEO|scandal|fraud|warning|downgrade|upgrade)\b',
    re.IGNORECASE
)

def compute_impact_score(sentiment_score, source_cred, is_primary, published_at, title):
    hours_old = (datetime.now(timezone.utc) - published_at).total_seconds() / 3600
    recency = math.exp(-0.05 * hours_old)
    keyword_w = 1.0 if HIGH_IMPACT_KEYWORDS.search(title) else 0.6
    sentiment_strength = abs(sentiment_score - 0.5) * 2

    raw = (0.35 * sentiment_strength +
           0.25 * source_cred +
           0.20 * (1.0 if is_primary else 0.5) +
           0.12 * recency +
           0.08 * keyword_w)

    impact_score = min(1.0, raw)
    level = "HIGH" if impact_score >= 0.70 else ("MEDIUM" if impact_score >= 0.40 else "LOW")
    return impact_score, level
```

**4.3 Gemini LLM Explanation Generation**

**System Prompt (stored as `prompt_version = "v1.0"`):**
```
You are a senior financial analyst AI. Your job is to explain how a news article 
impacts a specific stock in 2–3 concise sentences. Be factual, avoid speculation, 
and quantify impact where possible. Use plain English suitable for retail investors.
Format: One sentence for what happened, one for why it matters to the stock, 
one for short-term outlook (if determinable). Never recommend buying or selling.
```

**User Prompt Template:**
```python
def build_gemini_prompt(title, key_sentences, ticker, sentiment_label, company_name):
    return f"""
Article Title: {title}

Key Content: {' '.join(key_sentences[:3])}

Stock: {company_name} ({ticker})
Preliminary Sentiment: {sentiment_label}

Task: Explain in 2-3 sentences how this news specifically impacts {ticker}. 
Be precise about financial implications. Do not recommend any action.
"""
```

**Gemini API Call with Retry:**
```python
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def generate_explanation(prompt: str) -> str:
    response = await model.generate_content_async(
        prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=200,
            temperature=0.2,   # Low temp = factual, consistent
        )
    )
    return response.text.strip()
```

**Cost Control:** Use `gemini-1.5-flash` (cheapest). Only call LLM for `impact_level = HIGH or MEDIUM`. For LOW impact articles, skip LLM and use template: `"This {sentiment_label.lower()} news about {ticker} has {impact_level.lower()} expected market impact based on automated analysis."`

**Tools:** `transformers`, `torch`, `google-generativeai`, `tenacity`  
**Expected Outputs:**
- Every article has a `news_sentiment_analysis` row with sentiment + impact + explanation
- LLM explanations for HIGH/MEDIUM impact articles
- Celery task completion within 3 minutes of ingestion  
**Dependencies:** Phase 3 complete, GPU/CPU environment for FinBERT, Gemini API key

---

## Phase 5 — Reliability Scoring System

**Goal:** Implement the nightly batch that evaluates past predictions against actual price movements and updates reliability scores.

### Tasks

**5.1 Nightly Backtest Algorithm**

```python
# app/tasks/reliability.py

FLAT_THRESHOLD_PCT = 0.5  # ±0.5% = FLAT, not directional

def direction_from_pct(pct_change: float) -> str:
    if pct_change > FLAT_THRESHOLD_PCT:
        return "UP"
    elif pct_change < -FLAT_THRESHOLD_PCT:
        return "DOWN"
    return "FLAT"

def sentiment_to_expected_direction(label: str) -> str:
    return {"POSITIVE": "UP", "NEUTRAL": "FLAT", "NEGATIVE": "DOWN"}[label]

def is_prediction_correct(predicted_label: str, actual_direction: str) -> bool:
    expected = sentiment_to_expected_direction(predicted_label)
    if expected == "FLAT":
        return actual_direction == "FLAT"
    return expected == actual_direction

async def run_nightly_backtest():
    """Runs at 11 PM UTC. Scores articles published 24h and 72h ago."""
    
    # Step 1: Get articles from 24h ago whose reliability hasn't been scored at 24h window
    articles_24h = await db.fetch("""
        SELECT nsa.id, nsa.article_id, nsa.ticker, nsa.sentiment_label, na.published_at
        FROM news_sentiment_analysis nsa
        JOIN news_articles na ON nsa.article_id = na.id
        LEFT JOIN news_reliability_scores nrs ON nrs.sentiment_analysis_id = nsa.id
        WHERE na.published_at BETWEEN NOW() - INTERVAL '26 hours' AND NOW() - INTERVAL '22 hours'
          AND nrs.id IS NULL
          AND nsa.ticker IS NOT NULL
    """)
    
    for row in articles_24h:
        ticker = row.ticker
        pub_time = row.published_at
        
        # Step 2: Fetch price at publish time and 24h later from historical_prices
        price_at_pub = await get_price_at_time(ticker, pub_time)
        price_24h = await get_price_at_time(ticker, pub_time + timedelta(hours=24))
        price_72h = await get_price_at_time(ticker, pub_time + timedelta(hours=72))
        
        if not price_at_pub or not price_24h:
            continue
        
        pct_24h = ((price_24h - price_at_pub) / price_at_pub) * 100
        pct_72h = ((price_72h - price_at_pub) / price_at_pub) * 100 if price_72h else None
        
        dir_24h = direction_from_pct(pct_24h)
        dir_72h = direction_from_pct(pct_72h) if pct_72h else None
        
        correct_24h = is_prediction_correct(row.sentiment_label, dir_24h)
        correct_72h = is_prediction_correct(row.sentiment_label, dir_72h) if dir_72h else None
        
        # Step 3: Compute article-level reliability score
        # Weighted: 40% on 24h, 60% on 72h (72h is more meaningful)
        if correct_72h is not None:
            raw_score = 0.4 * int(correct_24h) + 0.6 * int(correct_72h)
        else:
            raw_score = float(int(correct_24h))
        
        # Step 4: Store result
        await db.execute("""
            INSERT INTO news_reliability_scores (
                sentiment_analysis_id, article_id, ticker, sentiment_predicted,
                price_at_publish, price_24h_later, price_72h_later,
                actual_movement_24h, actual_movement_72h,
                movement_direction_24h, movement_direction_72h,
                prediction_correct_24h, prediction_correct_72h,
                reliability_score, backtested_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,NOW())
        """, row.id, row.article_id, ticker, row.sentiment_label,
             price_at_pub, price_24h, price_72h, pct_24h, pct_72h,
             dir_24h, dir_72h, correct_24h, correct_72h, raw_score)
        
        # Step 5: Update aggregate source_reliability_stats
        await update_source_reliability(row.article_id, correct_24h, correct_72h)
        await update_model_reliability(row.sentiment_analysis_id, correct_24h, correct_72h)
```

**5.2 Aggregate Reliability Update**
```python
async def update_source_reliability(article_id, correct_24h, correct_72h):
    source = await get_article_source(article_id)
    await db.execute("""
        UPDATE source_reliability_stats SET
            total_articles = total_articles + 1,
            correct_24h = correct_24h + $1,
            correct_72h = correct_72h + $2,
            accuracy_24h = (correct_24h + $1)::float / (total_articles + 1),
            accuracy_72h = (correct_72h + $2)::float / (total_articles + 1),
            last_updated = NOW()
        WHERE source_name = $3
    """, int(correct_24h), int(correct_72h or 0), source)
```

**5.3 Per-Article Display Reliability Score**
The score shown in the UI for any given article = weighted blend:
```
display_reliability = 0.5 × article_reliability_score    (this article's own outcome)
                    + 0.3 × source_reliability_stats.accuracy_24h  (source avg)
                    + 0.2 × model_reliability_stats.accuracy_24h   (model avg)

If article not yet backtested (published < 24h ago):
  display_reliability = source_accuracy × 0.6 + model_accuracy × 0.4
  (shown with label "Estimated — final score in Xh")
```

**5.4 Price Data Fetcher (for backtest)**
```python
async def get_price_at_time(ticker: str, target_time: datetime) -> float | None:
    """
    Returns closing price of trading day closest to target_time.
    Uses historical_prices table first, then Alpha Vantage API as fallback.
    """
    target_date = target_time.date()
    # Skip weekends/holidays: find nearest prior trading day
    result = await db.fetchrow("""
        SELECT adj_close FROM historical_prices
        WHERE ticker = $1 AND date <= $2
        ORDER BY date DESC LIMIT 1
    """, ticker, target_date)
    return result['adj_close'] if result else None
```

**Tools:** `asyncpg`, `celery`, `yfinance` (for price fallback), `pandas`  
**Expected Outputs:**
- `news_reliability_scores` table populated nightly for all articles >24h old
- `source_reliability_stats` and `model_reliability_stats` updated
- UI-ready `display_reliability` score available on every article  
**Dependencies:** Phase 4 complete, `historical_prices` table populated and kept current

---

> **Document continues in [`implementationplan_part2.md`](./implementationplan_part2.md)**  
> Phases 6–10: Personalization Engine, Backend APIs, Filtering System, Testing & Backtesting, Deployment & Scaling — plus full API endpoint reference, cost optimization, and scalability planning.
