# FinSight — News System Implementation Plan (Part 2)
## Phases 6–10 | API Design | Filtering | Testing | Deployment | Scalability

> **Part 1:** [`implementationplan.md`](./implementationplan.md) — Architecture, DB Schema, Phases 1–5

---

## Phase 6 — Personalization Engine

**Goal:** Serve each user a news feed filtered to their portfolio tickers, subscribed sectors, and preferences.

### Tasks

**6.1 User Context Resolution**
At feed request time, resolve the user's personalization context:
```python
# app/services/personalization.py

async def get_user_news_context(user_id: str, db, redis) -> dict:
    """
    Returns a dict with the user's portfolio tickers and subscribed sectors.
    Cached in Redis for 5 minutes to avoid repeated DB hits per request.
    """
    cache_key = f"user_ctx:{user_id}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fetch portfolio holdings (from portfolio module — Garima's tables)
    portfolio_tickers = await db.fetch(
        "SELECT ticker FROM portfolio_holdings WHERE user_id = $1 AND is_active = TRUE",
        user_id
    )

    # Fetch watchlist tickers (this module also handles watchlist news)
    watchlist_tickers = await db.fetch(
        "SELECT ticker FROM watchlist_items WHERE user_id = $1",
        user_id
    )

    # Fetch sector subscriptions (user settings table)
    subscribed_sectors = await db.fetch(
        "SELECT sector_name FROM user_sector_subscriptions WHERE user_id = $1",
        user_id
    )

    context = {
        "portfolio_tickers": [r["ticker"] for r in portfolio_tickers],
        "watchlist_tickers": [r["ticker"] for r in watchlist_tickers],
        "all_tickers": list(set([...portfolio_tickers, ...watchlist_tickers])),
        "subscribed_sectors": [r["sector_name"] for r in subscribed_sectors],
    }

    await redis.setex(cache_key, 300, json.dumps(context))
    return context
```

**6.2 Three-Tier Feed Generation**
```python
async def get_personalized_feed(user_id: str, tier: str, filters: dict, db, redis) -> list:
    """
    tier: 'PORTFOLIO' | 'SECTOR' | 'GENERAL'
    filters: {impact_level, time_window_hours, min_reliability, sentiment}
    """
    ctx = await get_user_news_context(user_id, db, redis)
    
    # Build WHERE clause dynamically
    conditions = ["na.is_deleted = FALSE", "na.is_duplicate = FALSE"]
    params = []
    
    if tier == "PORTFOLIO":
        conditions.append(f"nst.ticker = ANY($1)")
        params.append(ctx["all_tickers"])
    elif tier == "SECTOR":
        conditions.append("nsect.sector_name = ANY($1)")
        params.append(ctx["subscribed_sectors"])
    # GENERAL: no additional WHERE clause
    
    # Apply user filters
    if filters.get("impact_level"):
        conditions.append(f"nsa.impact_level = '{ filters['impact_level'] }'")
    if filters.get("time_window_hours"):
        conditions.append(f"na.published_at >= NOW() - INTERVAL '{filters['time_window_hours']} hours'")
    if filters.get("min_reliability"):
        conditions.append(f"nrs.reliability_score >= {filters['min_reliability']}")
    if filters.get("sentiment"):
        conditions.append(f"nsa.sentiment_label = '{filters['sentiment']}'")
    
    query = f"""
        SELECT DISTINCT ON (na.id)
            na.id, na.title, na.source_name, na.published_at, na.image_url, na.source_url,
            nsa.sentiment_label, nsa.impact_level, nsa.impact_score,
            nsa.ai_explanation, nsa.sentiment_score,
            COALESCE(nrs.reliability_score, src.accuracy_24h) AS display_reliability
        FROM news_articles na
        LEFT JOIN news_stock_tags nst ON nst.article_id = na.id
        LEFT JOIN news_sector_tags nsect ON nsect.article_id = na.id
        LEFT JOIN news_sentiment_analysis nsa ON nsa.article_id = na.id
        LEFT JOIN news_reliability_scores nrs ON nrs.article_id = na.id
        LEFT JOIN source_reliability_stats src ON src.source_name = na.source_name
        WHERE {' AND '.join(conditions)}
        ORDER BY na.id, nsa.impact_score DESC, na.published_at DESC
        LIMIT 50
    """
    return await db.fetch(query, *params)
```

**6.3 Redis Feed Caching Strategy**
```python
CACHE_TTLS = {
    "PORTFOLIO": 300,   # 5 min — high personalization, stale quickly
    "SECTOR":    600,   # 10 min
    "GENERAL":   900,   # 15 min — same for all users, cache aggressively
}

async def get_cached_feed(user_id, tier, filters, db, redis):
    filter_hash = hashlib.md5(json.dumps(filters, sort_keys=True).encode()).hexdigest()[:8]
    cache_key = f"feed:{user_id}:{tier}:{filter_hash}"
    
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    data = await get_personalized_feed(user_id, tier, filters, db, redis)
    serialized = [dict(r) for r in data]  # asyncpg Record → dict
    await redis.setex(cache_key, CACHE_TTLS[tier], json.dumps(serialized, default=str))
    return serialized
```

**Expected Outputs:**
- News feed endpoint returns results in < 200ms (cached) or < 800ms (uncached)
- Three separate tab feeds: Portfolio News | Sector News | Market News
- Watchlist stocks treated same as portfolio for news purposes

---

## Phase 7 — Backend APIs

**Goal:** Expose all news intelligence functionality via clean, documented REST APIs.

### 7.1 FastAPI Router Structure

```
app/api/
├── routes/
│   ├── news_feed.py       (GET /news/feed)
│   ├── news_article.py    (GET /news/article/{id})
│   ├── news_filter.py     (GET /news/filter)
│   ├── reliability.py     (GET /news/reliability/...)
│   └── admin.py           (POST /admin/news/reprocess)
```

### 7.2 Complete API Endpoint Reference

---

#### `GET /api/v1/news/feed`
Returns the personalized three-tier news feed for the authenticated user.

**Query Parameters:**

| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| `tier` | string | Yes | — | `portfolio` \| `sector` \| `general` |
| `limit` | int | No | 20 | Max articles to return (max 50) |
| `offset` | int | No | 0 | Pagination offset |
| `impact_level` | string | No | — | `HIGH` \| `MEDIUM` \| `LOW` |
| `time_window` | int | No | 24 | Hours to look back (1–168) |
| `min_reliability` | float | No | 0.0 | Minimum reliability score (0.0–1.0) |
| `sentiment` | string | No | — | `POSITIVE` \| `NEUTRAL` \| `NEGATIVE` |

**Response (200 OK):**
```json
{
  "tier": "portfolio",
  "total": 14,
  "articles": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Apple Reports Record Q4 Earnings, Beats EPS Estimates",
      "source_name": "Reuters",
      "source_url": "https://reuters.com/...",
      "published_at": "2026-03-10T04:32:00Z",
      "image_url": "https://...",
      "sentiment": {
        "label": "POSITIVE",
        "score": 0.87,
        "impact_level": "HIGH",
        "impact_score": 0.81
      },
      "tickers": ["AAPL"],
      "sectors": ["Technology"],
      "ai_explanation": "Apple's Q4 EPS of $1.64 beat consensus estimates of $1.56 by 5.1%, driven by services revenue growth of 13% YoY. This is bullish for AAPL in the near term as it signals margin expansion. Short-term price pressure may ease if this beats analyst expectations across the board.",
      "reliability": {
        "score": 0.73,
        "is_estimated": false,
        "label": "High Reliability"
      },
      "category": "PORTFOLIO"
    }
  ]
}
```

---

#### `GET /api/v1/news/article/{article_id}`
Returns full details for a single article.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "title": "...",
  "summary": "...",
  "source_name": "Reuters",
  "source_url": "https://...",
  "author": "Jane Smith",
  "published_at": "2026-03-10T04:32:00Z",
  "image_url": "...",
  "tickers": [
    { "ticker": "AAPL", "is_primary": true, "mention_count": 8 }
  ],
  "sectors": ["Technology"],
  "sentiment": {
    "label": "POSITIVE",
    "score": 0.87,
    "positive_score": 0.87,
    "neutral_score": 0.09,
    "negative_score": 0.04,
    "impact_level": "HIGH",
    "impact_score": 0.81,
    "ai_explanation": "Apple's Q4 EPS...",
    "analyzed_at": "2026-03-10T04:35:42Z"
  },
  "reliability": {
    "score": 0.73,
    "is_estimated": false,
    "source_accuracy": 0.68,
    "model_accuracy": 0.71,
    "backtested_at": "2026-03-09T23:00:00Z"
  }
}
```

---

#### `GET /api/v1/news/filter`
Advanced filtering endpoint (used by the filter drawer in UI).

**Query Parameters:** Same as `/news/feed` plus:

| Param | Type | Description |
|---|---|---|
| `tickers` | string (comma-sep) | Filter by specific tickers: `AAPL,MSFT` |
| `sectors` | string (comma-sep) | Filter by sectors: `Technology,Healthcare` |
| `sources` | string (comma-sep) | Filter by source: `Reuters,CNBC` |
| `sort_by` | string | `published_at` \| `impact_score` \| `reliability_score` |
| `sort_order` | string | `asc` \| `desc` |

---

#### `GET /api/v1/news/reliability/source/{source_name}`
Returns reliability stats for a specific news source.

**Response:**
```json
{
  "source_name": "Reuters",
  "total_articles_scored": 1284,
  "accuracy_24h": 0.68,
  "accuracy_72h": 0.71,
  "avg_impact_score": 0.62,
  "reliability_tier": "HIGH",
  "last_updated": "2026-03-10T23:00:00Z"
}
```

---

#### `GET /api/v1/news/reliability/ticker/{ticker}`
Returns rolling reliability stats for a given ticker's news predictions.

**Response:**
```json
{
  "ticker": "AAPL",
  "total_predictions": 320,
  "correct_24h": 218,
  "accuracy_24h": 0.681,
  "correct_72h": 236,
  "accuracy_72h": 0.737,
  "by_sentiment": {
    "POSITIVE": { "accuracy_24h": 0.72, "count": 145 },
    "NEUTRAL":  { "accuracy_24h": 0.64, "count": 91 },
    "NEGATIVE": { "accuracy_24h": 0.65, "count": 84 }
  }
}
```

---

#### `POST /api/v1/news/interactions`
Records user interaction with an article (saved, dismissed, viewed).

**Request Body:**
```json
{ "article_id": "uuid", "interaction": "saved" }
```

---

#### `GET /api/v1/news/watchlist-feed`
Returns news for the user's watchlist stocks (same tier system, separate endpoint for Watchlist module).

---

#### `POST /api/v1/admin/news/reprocess/{article_id}`
Admin-only: re-run NLP + sentiment pipeline for a specific article (useful after model updates).

---

### 7.3 Authentication Middleware
All `/api/v1/news/*` endpoints require JWT authentication (Pratyaksha's auth module). FastAPI dependency:

```python
from fastapi import Depends, HTTPException
from app.core.auth import verify_token  # shared util

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload  # {"user_id": "...", "role": "student"|"adult"|"guardian"}
```

---

## Phase 8 — Filtering System

**Goal:** Implement multi-dimensional, composable filtering for the news feed UI.

### 8.1 Filter Dimensions

| Filter | Type | Options | DB Column |
|---|---|---|---|
| Impact Level | Select | HIGH / MEDIUM / LOW | `nsa.impact_level` |
| Time Window | Slider | 1h / 6h / 24h / 48h / 7d / 30d | `na.published_at >= NOW() - INTERVAL` |
| Reliability Score | Slider | 0.0 – 1.0 (min threshold) | `nrs.reliability_score` |
| Sentiment | Multi-select | POSITIVE / NEUTRAL / NEGATIVE | `nsa.sentiment_label` |
| Sector | Multi-select | All GICS sectors | `nsect.sector_name` |
| Source | Multi-select | All ingested sources | `na.source_name` |
| Sort By | Select | Newest / Highest Impact / Highest Reliability | `ORDER BY` clause |

### 8.2 Composable Filter Builder (Backend)

```python
# app/services/filter_builder.py

class NewsFilterBuilder:
    def __init__(self):
        self.conditions = []
        self.params = []
        self.param_counter = 1

    def _p(self, value):
        """Registers parameter and returns its placeholder."""
        self.params.append(value)
        placeholder = f"${self.param_counter}"
        self.param_counter += 1
        return placeholder

    def add_impact(self, levels: list[str]):
        if levels:
            placeholders = ", ".join(self._p(l) for l in levels)
            self.conditions.append(f"nsa.impact_level IN ({placeholders})")
        return self

    def add_time_window(self, hours: int):
        if hours:
            self.conditions.append(f"na.published_at >= NOW() - INTERVAL '{hours} hours'")
        return self

    def add_min_reliability(self, min_score: float):
        if min_score > 0:
            self.conditions.append(f"COALESCE(nrs.reliability_score, src.accuracy_24h) >= {self._p(min_score)}")
        return self

    def add_sentiments(self, labels: list[str]):
        if labels:
            placeholders = ", ".join(self._p(l) for l in labels)
            self.conditions.append(f"nsa.sentiment_label IN ({placeholders})")
        return self

    def add_tickers(self, tickers: list[str]):
        if tickers:
            self.conditions.append(f"nst.ticker = ANY({self._p(tickers)})")
        return self

    def build_where(self) -> str:
        base = ["na.is_deleted = FALSE", "na.is_duplicate = FALSE"]
        all_conditions = base + self.conditions
        return " AND ".join(all_conditions)

    def get_params(self):
        return self.params
```

### 8.3 Frontend Filter State (for Siddhi's UI reference)

```typescript
interface NewsFilters {
  tier: 'portfolio' | 'sector' | 'general';
  impactLevels: ('HIGH' | 'MEDIUM' | 'LOW')[];
  sentiments: ('POSITIVE' | 'NEUTRAL' | 'NEGATIVE')[];
  timeWindowHours: 1 | 6 | 24 | 48 | 168 | 720;
  minReliability: number;  // 0.0–1.0 slider value
  sectors: string[];
  sortBy: 'published_at' | 'impact_score' | 'reliability_score';
  sortOrder: 'asc' | 'desc';
}
```

---

## Phase 9 — Testing & Backtesting

**Goal:** Validate system correctness, model accuracy, and pipeline reliability.

### 9.1 Unit Tests

```
tests/
├── test_deduplicator.py       # Hash collision, normalization edge cases
├── test_nlp_pipeline.py       # Ticker extraction accuracy  
├── test_sentiment.py          # FinBERT output parsing
├── test_impact_score.py       # Score formula boundary conditions
├── test_filter_builder.py     # SQL injection safety, composition
├── test_reliability_batch.py  # Backtest algorithm correctness
└── test_api_endpoints.py      # Integration tests with test DB
```

**Key Test Cases:**
```python
# test_nlp_pipeline.py
def test_ticker_extraction():
    cases = [
        ("Apple reports earnings", "Apple Inc.", ["AAPL"]),
        ("TSLA and MSFT diverge on AI news", None, ["TSLA", "MSFT"]),
        ("Fed raises rates by 25bps", None, []),  # No ticker expected
    ]
    for title, body, expected in cases:
        result = extract_tickers_from_article(body or "", title)
        extracted = [r["ticker"] for r in result]
        assert set(extracted) == set(expected), f"Failed for: {title}"

# test_impact_score.py
def test_impact_boundaries():
    # Earnings keyword + high credibility source = HIGH
    score, level = compute_impact_score(0.9, 0.92, True, datetime.utcnow(), "Apple earnings beat")
    assert level == "HIGH"
    
    # Weak sentiment + low credibility reddit post = LOW
    score, level = compute_impact_score(0.52, 0.35, False, datetime.utcnow(), "AAPL looking bullish")
    assert level == "LOW"
```

### 9.2 Model Evaluation Metrics

Run quarterly or after each model update:

| Metric | Target | Tool |
|---|---|---|
| FinBERT Sentiment Accuracy (F1) | > 0.78 on FinancialPhraseBank test set | `sklearn.metrics.f1_score` |
| Sentiment → Price Direction Accuracy (24h) | > 60% (random = 33%) | Backtest batch |
| Sentiment → Price Direction Accuracy (72h) | > 63% | Backtest batch |
| Pipeline Latency (p99 ingestion→analysis) | < 5 minutes | Prometheus histogram |
| Deduplication Rate | > 80% | `ingestion_job_log` |
| API p99 Latency (feed endpoint) | < 500ms | FastAPI metrics |

### 9.3 FinBERT Fine-Tuning Evaluation
```python
from sklearn.metrics import classification_report
from datasets import load_dataset

# Load FinancialPhraseBank dataset
dataset = load_dataset("financial_phrasebank", "sentences_allagree")
test_texts = dataset["train"].filter(lambda x: x["label"] != -1)["sentence"]
test_labels = dataset["train"].filter(lambda x: x["label"] != -1)["label"]

# Map FinancialPhraseBank labels: 0=negative, 1=neutral, 2=positive
LABEL_MAP = {0: "NEGATIVE", 1: "NEUTRAL", 2: "POSITIVE"}

predictions = [classify_sentiment([t])["sentiment_label"] for t in test_texts]
print(classification_report(
    [LABEL_MAP[l] for l in test_labels], predictions,
    target_names=["NEGATIVE", "NEUTRAL", "POSITIVE"]
))
```

### 9.4 Backtesting Historical Accuracy Report

Run after 30 days of production data:
```python
# scripts/backtest_report.py
async def generate_accuracy_report():
    results = await db.fetch("""
        SELECT 
            sentiment_predicted,
            COUNT(*) as total,
            SUM(CASE WHEN prediction_correct_24h THEN 1 ELSE 0 END) as correct_24h,
            AVG(actual_movement_24h) as avg_movement,
            STDDEV(actual_movement_24h) as stddev_movement
        FROM news_reliability_scores
        WHERE backtested_at >= NOW() - INTERVAL '30 days'
        GROUP BY sentiment_predicted
    """)
    
    # Print confusion-matrix style table:
    # Predicted POSITIVE → Actual UP: X%, DOWN: Y%, FLAT: Z%
```

---

## Phase 10 — Deployment & Scaling

**Goal:** Deploy to production with observability, horizontal scaling, and cost controls.

### 10.1 Docker Compose (Development)

```yaml
# docker-compose.yml
version: '3.9'
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/finsight
      - MONGO_URI=mongodb://mongo:27017/finsight
      - REDIS_URL=redis://redis:6379
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - NEWSAPI_KEY=${NEWSAPI_KEY}
    depends_on: [postgres, mongo, redis]

  celery-worker:
    build: .
    command: celery -A celery_app worker --loglevel=info --concurrency=4
    depends_on: [redis, postgres, mongo]

  celery-beat:
    build: .
    command: celery -A celery_app beat --loglevel=info
    depends_on: [redis]

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: finsight
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes: [./data/postgres:/var/lib/postgresql/data]

  mongo:
    image: mongo:7
    volumes: [./data/mongo:/data/db]

  redis:
    image: redis:7-alpine
    volumes: [./data/redis:/data]
```

### 10.2 Production Architecture (AWS)

```
┌────────────────────────────────────────────────────────┐
│                  AWS Production Setup                   │
│                                                         │
│  [CloudFront CDN]                                       │
│         │                                               │
│  [ALB (Application Load Balancer)]                      │
│         │                                               │
│  [ECS Fargate] ←── FastAPI (2–4 tasks, auto-scale)     │
│         │                                               │
│  [ECS Fargate] ←── Celery Workers (2–8 tasks)          │
│         │                                               │
│  [ElastiCache Redis] ← Cache + Queue broker             │
│  [RDS PostgreSQL 15] ← Primary DB (Multi-AZ)           │
│  [DocumentDB / Atlas] ← MongoDB                         │
└────────────────────────────────────────────────────────┘
```

### 10.3 PostgreSQL Partitioning Strategy

Since `news_articles` and `news_reliability_scores` will grow large (millions of rows), partition by month:

```sql
-- Partition news_articles by published_at month
CREATE TABLE news_articles (
    ...
    published_at TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (published_at);

CREATE TABLE news_articles_2026_03 PARTITION OF news_articles
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Drop partitions older than 2 years automatically via pg_cron
SELECT cron.schedule('drop-old-partitions', '0 1 1 * *',
    $$DELETE FROM news_articles WHERE published_at < NOW() - INTERVAL '2 years'$$);
```

### 10.4 Scalability Planning

| Component | Current Capacity | Scale Trigger | Scale Action |
|---|---|---|---|
| Celery Workers | 2 workers × 4 concurrency | Queue depth > 500 tasks | Add ECS task (up to 8) |
| FastAPI | 2 tasks | CPU > 70% | ECS auto-scaling to 4 |
| Redis | ElastiCache r6g.large | Memory > 80% | Upgrade to r6g.xlarge |
| PostgreSQL | db.t4g.medium | CPU > 60% or connections > 80% | Add read replicas |
| FinBERT Inference | CPU-bound on Celery | p99 latency > 30s | Add GPU-enabled worker |

### 10.5 Cost Optimization

| Strategy | Savings |
|---|---|
| Use `gemini-1.5-flash` (not Pro) for explanations | ~10× cheaper vs Gemini Pro |
| Skip LLM for LOW impact articles | ~40% fewer API calls |
| NewsAPI paid tier only if free limits insufficient | $0 to ~$449/mo depending on volume |
| Use `yfinance` (free) for historical price data fallback | $0 vs paid data feeds |
| PostgreSQL partitioning + TTL cleanup | Keeps DB size manageable |
| Redis TTL-based eviction | Avoids unbounded memory growth |
| Cache general market feed aggressively (15 min) | Reduces DB load by ~60% for that tier |

**Estimated Monthly Cost (MVP scale, ~500 stocks, 10k users):**
| Service | Cost |
|---|---|
| NewsAPI (Developer plan) | ~$449/mo |
| Alpha Vantage (Premium) | ~$50/mo |
| Gemini API (flash, ~100k calls/mo) | ~$10–20/mo |
| AWS RDS t4g.medium (PostgreSQL) | ~$50/mo |
| AWS ElastiCache r6g.large (Redis) | ~$110/mo |
| AWS ECS Fargate (API + Celery) | ~$80/mo |
| MongoDB Atlas M20 | ~$57/mo |
| **Total** | **~$800–900/mo** |

> **Student project alternative:** Use free tiers only — NewsAPI free (100 req/day), yfinance (no API key), Gemini free tier, Railway free tier / Render free tier → **~$0/mo** with reduced fresh-data volume.

### 10.6 Monitoring & Alerting

```python
# Prometheus metrics exposed at /metrics
from prometheus_client import Counter, Histogram, Gauge

articles_ingested = Counter('news_articles_ingested_total', 'Articles ingested', ['source'])
sentiment_latency = Histogram('sentiment_analysis_seconds', 'FinBERT inference latency')
llm_latency = Histogram('llm_explanation_seconds', 'Gemini API latency')
queue_depth = Gauge('celery_queue_depth', 'Pending Celery tasks')
reliability_accuracy = Gauge('model_accuracy_24h', 'Rolling 24h prediction accuracy')
```

**Grafana Alerts:**
- Celery queue depth > 1000 for > 15 min → PagerDuty alert
- API p99 latency > 2s → Slack alert
- Gemini API error rate > 5% → Slack alert
- Nightly batch not completed by 11:30 PM UTC → PagerDuty alert

### 10.7 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=app --cov-report=xml
      - run: python -m spacy download en_core_web_lg

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker image
        run: docker build -t finsight-news:${{ github.sha }} .
      - name: Push to ECR
        run: aws ecr get-login-password | docker login ... && docker push ...
      - name: Deploy to ECS
        run: aws ecs update-service --cluster finsight --service news-api --force-new-deployment
```

---

## Reliability Score — Feedback Loop for Continuous Improvement

**Goal:** Use backtested outcomes to continuously improve the model and prompts.

### Feedback Mechanism

```
Every 30 days, run model evaluation report:
  - If accuracy_24h < 58% for 2 consecutive months:
      → Trigger fine-tuning of FinBERT on recent correctly-labeled articles
      → Update prompt_version in gemini calls
      → Run A/B test: new prompt_version vs old, compare accuracy on holdout set

Fine-tuning approach:
  1. Pull all news_reliability_scores where prediction_correct_24h IS NOT NULL
  2. Join with news_articles for text + news_sentiment_analysis for predicted label
  3. Articles where prediction was WRONG → use actual_direction as corrected label
  4. Collect 500+ such corrected examples
  5. Fine-tune FinBERT using HuggingFace Trainer:
      model.train(corrected_dataset, epochs=3, learning_rate=2e-5)
  6. Evaluate new model on held-out test set
  7. If F1 improves by > 2%, deploy new weights
```

```python
# scripts/retrain_finbert.py
def prepare_fine_tune_dataset():
    """Extracts correctly-labeled examples for fine-tuning from backtested data."""
    rows = db.execute("""
        SELECT na.title, key_sentences_json, 
               CASE 
                 WHEN nrs.prediction_correct_24h THEN nsa.sentiment_label
                 ELSE CASE nrs.movement_direction_24h
                        WHEN 'UP'   THEN 'POSITIVE'
                        WHEN 'DOWN' THEN 'NEGATIVE'
                        ELSE 'NEUTRAL'
                      END
               END AS corrected_label
        FROM news_reliability_scores nrs
        JOIN news_sentiment_analysis nsa ON nsa.id = nrs.sentiment_analysis_id
        JOIN news_articles na ON na.id = nrs.article_id
        WHERE nrs.backtested_at >= NOW() - INTERVAL '30 days'
        LIMIT 2000
    """)
    return [{"text": r.title, "label": r.corrected_label} for r in rows]
```

---

## Summary: What Lives Where (Data Storage A-to-Z Reference)

| Data Type | Storage | Table/Collection | Retention |
|---|---|---|---|
| Article metadata (title, URL, source, timestamps) | PostgreSQL | `news_articles` | 2 years |
| Full article text + HTML | MongoDB | `raw_articles` | 2 years |
| Stock ticker tags per article | PostgreSQL | `news_stock_tags` | 2 years |
| Sector tags per article | PostgreSQL | `news_sector_tags` | 2 years |
| Sentiment + impact + AI explanation | PostgreSQL | `news_sentiment_analysis` | 2 years |
| Reliability backtest outcomes | PostgreSQL | `news_reliability_scores` | 2 years |
| Aggregate source reliability stats | PostgreSQL | `source_reliability_stats` | Permanent |
| Aggregate model reliability stats | PostgreSQL | `model_reliability_stats` | Permanent |
| User article interactions | PostgreSQL | `user_news_interactions` | 1 year |
| Ticker → Sector mapping | PostgreSQL | `ticker_sector_map` | Permanent, quarterly update |
| Historical stock prices | PostgreSQL | `historical_prices` | 5 years |
| Ingestion job audit log | PostgreSQL | `ingestion_job_log` | 90 days |
| User portfolio/watchlist/sector context | Redis | `user_ctx:{user_id}` | 5 min TTL |
| Personalized news feed results | Redis | `feed:{user_id}:{tier}:{filter_hash}` | 5–15 min TTL |
| Per-article enriched JSON (hot) | Redis | `article:{article_id}` | 30 min TTL |
| Source reliability scores (hot) | Redis | `reliability:source:{source}` | 1 hour TTL |
| Deduplication bloom filter | Redis | `dedup:hash:{sha256}` | 48 hour TTL |
| API rate limit counters | Redis | `rate_limit:{api_name}` | 60 sec window |
| NLP entities + key sentences | MongoDB | `raw_articles.nlp_entities` | With parent doc |
| Training/fine-tuning dataset | MongoDB | `training_articles` | Permanent |
| FinBERT model weights | Filesystem/S3 | `models/finbert-finsight/` | Versioned |

---

## Quick Start for Implementation (Day 1 Checklist)

```bash
# 1. Clone / init project
mkdir finsight-news && cd finsight-news
python -m venv venv && source venv/Scripts/activate  # Windows

# 2. Install dependencies
pip install fastapi uvicorn celery[redis] sqlalchemy asyncpg alembic \
            pydantic pymongo motor redis httpx feedparser \
            newspaper3k spacy transformers torch sentence-transformers \
            google-generativeai tenacity pandas yfinance \
            pytest pytest-asyncio pytest-cov

python -m spacy download en_core_web_lg

# 3. Start infrastructure
docker-compose up -d  # PostgreSQL + MongoDB + Redis

# 4. Run DB migrations
alembic upgrade head

# 5. Populate ticker_sector_map
python scripts/populate_ticker_map.py --source sp500

# 6. Fetch historical prices (one-time)
python scripts/fetch_historical_prices.py --years 5

# 7. Start Celery worker + beat
celery -A celery_app worker --loglevel=info &
celery -A celery_app beat --loglevel=info &

# 8. Start FastAPI
uvicorn main:app --reload --port 8000

# 9. Run tests
pytest tests/ -v
```

---

## Key Environment Variables (.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/finsight
MONGO_URI=mongodb://localhost:27017/finsight
REDIS_URL=redis://localhost:6379

# News APIs
NEWSAPI_KEY=your_newsapi_key_here
ALPHA_VANTAGE_KEY=your_alpha_vantage_key_here
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=FinSight/1.0

# AI
GEMINI_API_KEY=your_gemini_api_key_here

# App
SECRET_KEY=your_jwt_secret_key
ENVIRONMENT=development  # development | production
LOG_LEVEL=INFO
```

---

*Document generated for FinSight Project — Heena (Data Engineering & News Aggregation)*  
*Last updated: March 2026*
