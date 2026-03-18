# FinSight News Module

Intelligent News Aggregation and Analysis System for FinSight.

## Overview

FinSight is a comprehensive financial news intelligence pipeline that aggregates news from multiple sources, performs AI-powered analysis, and delivers personalized news feeds with reliability scoring. The system uses machine learning for sentiment analysis, automatic ticker extraction, and predictive reliability scoring.

## System Architecture

```
+------------------+--------------------+----------------------+
|  News Sources    |  Ingestion Layer  |  Processing Layer   |
+------------------+--------------------+----------------------+
| - NewsAPI        | - Celery Beat      | - spaCy (NER)       |
| - RSS Feeds     | - Celery Workers   | - FinBERT            |
| - Reddit        | - Redis Queue      | - Gemini AI         |
| - Alpha Vantage | - Deduplication    | - Impact Scoring    |
| - SEC EDGAR     |                    |                      |
+------------------+--------------------+----------------------+
         |                   |                   |
         v                   v                   v
+------------------+--------------------+----------------------+
|  PostgreSQL      |  MongoDB           |  Redis               |
|  (Metadata)      |  (Raw Articles)    |  (Cache/Queue)       |
+------------------+--------------------+----------------------+
                         |
                         v
+-----------------------------------------------------------+
|                    FastAPI Backend                         |
|  /api/v1/news/feed  /api/v1/news/article/{id}           |
|  /api/v1/news/filter  /api/v1/reliability/...            |
+-----------------------------------------------------------+
```

## Core Features

### 1. Multi-Source News Ingestion
- NewsAPI integration for mainstream financial news
- RSS feed scraping (Yahoo Finance, Google News)
- Reddit API integration for community discussions
- Alpha Vantage news sentiment data
- SEC EDGAR filings integration
- Automatic deduplication using Redis-based hashing

### 2. NLP Processing Pipeline
- Automatic stock ticker extraction using spaCy NER
- Company name to ticker mapping
- Sector and industry classification
- Key sentence extraction

### 3. AI-Powered Analysis
- Sentiment classification using FinBERT
- Impact score calculation (0-1 scale)
- Gemini AI-generated impact explanations
- Source credibility weighting

### 4. Reliability Scoring System
- Automatic backtesting against 24-hour stock price movements
- Per-article accuracy tracking
- Source reliability statistics
- Rolling accuracy metrics

### 5. Personalization Engine
- User-specific news feeds based on portfolio holdings
- Sector subscription filtering
- Custom watchlist support
- Tiered categorization (Portfolio, Sector, General)

## Technology Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| Task Queue | Celery + Celery Beat |
| Database | PostgreSQL (Neon), MongoDB (Atlas) |
| Cache | Redis (Upstash) |
| NLP/ML | spaCy, FinBERT, Transformers |
| AI | Google Gemini API |
| Containerization | Docker, Docker Compose |

## Prerequisites

- Python 3.11 or higher
- Docker Desktop (for containerized deployment)
- PostgreSQL database (Neon cloud recommended)
- MongoDB database (Atlas cloud recommended)
- Redis cache (Upstash cloud recommended)

### Required API Keys
- NewsAPI key (https://newsapi.org/)
- Reddit API credentials (https://www.reddit.com/prefs/apps)
- Gemini API key (https://aistudio.google.com/app/apikey)
- Alpha Vantage API key (https://www.alphavantage.co/)

## Environment Configuration

### 1. Copy Environment Template

```bash
cp .env.example .env
```

### 2. Configure Environment Variables

Edit the `.env` file with your credentials:

```bash
# Database & Cache (Cloud services)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/finsight
MONGO_URI=mongodb://host:27017/finsight
REDIS_URL=redis://host:6379/0

# API Keys
NEWSAPI_KEY=your_newsapi_key
ALPHA_VANTAGE_KEY=your_alpha_vantage_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
GEMINI_API_KEY=your_gemini_api_key

# Application Settings
SECRET_KEY=your_secret_key_here
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## Installation & Running

### Option A: Docker Deployment (Recommended)

1. Build the Docker images:
```bash
docker-compose build
```

2. Start all services:
```bash
docker-compose up -d
```

3. Verify services are running:
```bash
docker-compose ps
```

4. View logs:
```bash
docker-compose logs -f
```

5. Stop services:
```bash
docker-compose down
```

### Option B: Local Development

1. Create and activate virtual environment:
```bash
python -m venv .venv

# Linux/Mac
source .venv/bin/activate

# Windows
.venv\Scripts\Activate.ps1
```

2. Install dependencies:
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

3. Start the API server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

4. Start Celery worker (in a new terminal):
```bash
celery -A celery_app worker --loglevel=info -P solo
```

5. Start Celery Beat scheduler (in a new terminal):
```bash
celery -A celery_app beat --loglevel=info
```

## Scheduled Tasks

The Celery Beat scheduler runs the following periodic tasks:

| Task | Frequency | Description |
|------|-----------|-------------|
| newsapi-poll | Every 5 minutes | Fetches latest news from NewsAPI |
| yahoo-rss-scrape | Every 10 minutes | Scrapes Yahoo Finance RSS feeds |
| reddit-poll | Every 15 minutes | Collects posts from Reddit finance communities |
| alpha-vantage-poll | Every 15 minutes | Fetches sentiment data from Alpha Vantage |
| sec-edgar-poll | Every 30 minutes | Fetches SEC filings |
| reliability-batch | Daily 11:00 PM UTC | Runs backtesting and reliability scoring |

## API Endpoints

### Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check endpoint |
| GET | / | Redirects to UI |
| GET | /ui | Web interface |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/token | Generate JWT token |

**Token Request:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "student"
}
```

**Token Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "student"
}
```

### News Feed

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/news/feed | Personalized news feed |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| tier | string | No | general | portfolio, sector, general |
| tickers | list[string] | No | - | Filter by tickers |
| sector | string | No | - | Filter by sector |
| user_id | uuid | No | - | User ID for personalization |
| impact_level | string | No | - | HIGH, MEDIUM, LOW |
| time_window | int | No | 24 | Hours to look back (1-168) |
| min_reliability | float | No | 0.0 | Minimum reliability (0.0-1.0) |
| sentiment | string | No | - | POSITIVE, NEUTRAL, NEGATIVE |
| limit | int | No | 20 | Max articles (1-50) |
| offset | int | No | 0 | Pagination offset |

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/news/feed?tier=portfolio&tickers=AAPL,MSFT&limit=10"
```

### News Article Detail

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/news/article/{id} | Get article details |

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/news/article/550e8400-e29b-41d4-a716-446655440000"
```

### News Filter

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/news/filter | Advanced filtering |

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| tickers | string | Comma-separated tickers |
| sectors | string | Comma-separated sectors |
| sources | string | Comma-separated sources |
| impact_level | string | HIGH, MEDIUM, LOW |
| sentiment | string | POSITIVE, NEUTRAL, NEGATIVE |
| time_window | int | Hours to look back |
| min_reliability | float | Minimum reliability score |
| sort_by | string | published_at, impact_score, reliability_score |
| sort_order | string | asc, desc |

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/news/filter?tickers=AAPL&impact_level=HIGH&sort_by=reliability_score&sort_order=desc"
```

### Reliability Stats

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/reliability/source/{name} | Source reliability |
| GET | /api/v1/reliability/ticker/{ticker} | Ticker prediction history |

**Example Requests:**
```bash
curl "http://localhost:8000/api/v1/reliability/source/Reuters"
curl "http://localhost:8000/api/v1/reliability/ticker/AAPL"
```

### Interactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/interactions | Track user interactions |

**Request Body:**
```json
{
  "article_id": "uuid",
  "interaction": "saved"
}
```

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/admin/status | System status |

## Response Examples

### News Feed Response
```json
{
  "tier": "portfolio",
  "total": 14,
  "articles": [
    {
      "id": "uuid",
      "title": "Apple Reports Record Q4 Earnings",
      "source_name": "Reuters",
      "source_url": "https://reuters.com/...",
      "published_at": "2026-03-18T12:00:00Z",
      "image_url": "https://...",
      "sentiment": {
        "label": "POSITIVE",
        "score": 0.87,
        "impact_level": "HIGH",
        "impact_score": 0.81
      },
      "tickers": ["AAPL"],
      "sectors": ["Technology"],
      "ai_explanation": "Apple's Q4 EPS beat estimates...",
      "reliability": {
        "score": 0.73,
        "is_estimated": false
      }
    }
  ]
}
```

### Reliability Response
```json
{
  "source_name": "Reuters",
  "total_articles_scored": 1284,
  "accuracy_24h": 0.68,
  "accuracy_72h": 0.71,
  "avg_impact_score": 0.62,
  "reliability_tier": "HIGH"
}
```

## Running Tests

Run unit tests:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_filter_builder.py -v
```

## Project Structure

```
finsight/
├── app/
│   ├── api/
│   │   └── routes/           # FastAPI route definitions
│   │       ├── admin.py
│   │       ├── interactions.py
│   │       ├── news_article.py
│   │       ├── news_feed.py
│   │       ├── news_filter.py
│   │       └── reliability.py
│   ├── core/                 # Configuration, database connections
│   │   ├── auth.py          # JWT authentication
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── mongodb.py
│   │   └── redis.py
│   ├── ingestion/           # News source clients
│   │   ├── alpha_vantage_client.py
│   │   ├── base_client.py
│   │   ├── newsapi_client.py
│   │   ├── reddit_client.py
│   │   ├── rss_scraper.py
│   │   └── sec_client.py
│   ├── models/              # Database schemas and API models
│   │   ├── api_models.py
│   │   └── schemas.py
│   ├── processing/          # NLP, sentiment, deduplication
│   │   ├── deduplicator.py
│   │   ├── nlp_pipeline.py
│   │   ├── normalizer.py
│   │   ├── rate_limiter.py
│   │   └── sentiment_engine.py
│   ├── services/            # Business logic services
│   │   ├── filter_builder.py
│   │   └── personalization.py
│   ├── tasks/               # Celery task definitions
│   │   ├── ingest.py
│   │   ├── process.py
│   │   └── reliability.py
│   ├── ui/                  # Web interface
│   └── main.py              # FastAPI application entry point
├── tests/                   # Unit tests
│   ├── test_deduplicator.py
│   ├── test_filter_builder.py
│   └── test_impact_score.py
├── alembic/                 # Database migrations
├── docs/                    # Documentation
├── scripts/                 # Maintenance and utility scripts
├── celery_app.py            # Celery configuration
├── docker-compose.yml       # Docker compose configuration
├── Dockerfile               # Docker image definition
└── requirements.txt         # Python dependencies
```

## Troubleshooting

### Database Connection Issues
- Verify DATABASE_URL, MONGO_URI, and REDIS_URL are correctly configured
- Ensure cloud databases allow connections from your IP
- Check that .env file is in the project root

### Celery Worker Not Processing Tasks
- Ensure Redis is running and accessible
- Check Celery worker logs for errors
- Verify celery_app.py includes all task modules

### API Keys Not Working
- Confirm API keys are valid and have not expired
- Check rate limits for NewsAPI and Reddit
- Verify Gemini API has sufficient quota

### Missing Dependencies
If you encounter import errors, install the required packages:
```bash
pip install python-jose greenlet
```

## Verification

After starting the application, verify it's working:

- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Web UI: http://localhost:8000/ui

## License

Copyright 2026 FinSight. All rights reserved.
