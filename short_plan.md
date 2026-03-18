# FinSight — News System: Short Plan

> Sequential steps to build the Intelligent News Aggregation & Analysis System.

---

## Step 1 — Set Up the Project
- Initialize Python project with FastAPI
- Set up PostgreSQL, MongoDB, and Redis (via Docker)
- Configure `.env` with all API keys (NewsAPI, Alpha Vantage, Gemini, Reddit)

## Step 2 — Prepare the Data Foundation
- Populate the ticker → sector mapping table (S&P 500 list)
- Fetch 5 years of historical stock prices and store them
- Assign a starting credibility score to each known news source

## Step 3 — Build the News Ingestion Pipeline
- Connect to all news sources (NewsAPI, Yahoo RSS, Google RSS, Reddit, SEC)
- Schedule automatic polling every 5–15 minutes using Celery Beat
- Deduplicate articles using SHA-256 hashing before storing
- Save raw article text to MongoDB; save metadata to PostgreSQL

## Step 4 — Build the NLP Pipeline
- For each new article, extract stock tickers and company names mentioned
- Map tickers to their sectors
- Identify the top 3–5 key sentences from the article

## Step 5 — Build the Sentiment & Impact Engine
- Run FinBERT on the key sentences → get Positive / Neutral / Negative label
- Calculate an impact score (0–1) based on sentiment strength, source credibility, recency, and keywords
- For HIGH/MEDIUM impact articles, call Gemini API to generate a plain-English AI explanation
- Store all results (sentiment, impact score, AI explanation) in the database

## Step 6 — Build the Three-Tier Categorization
- Tag each article as **Portfolio**, **Sector**, or **General** based on the user's holdings and sector subscriptions
- This categorization is done at feed-fetch time (per user), not at ingestion time

## Step 7 — Build the Reliability Scoring System
- Every night, check articles published 24h and 72h ago
- Fetch the actual stock price movement for each predicted ticker
- Compare predicted sentiment direction vs actual price direction
- Store the outcome (correct/incorrect) and compute a reliability score per article
- Update rolling accuracy stats per news source and per AI model

## Step 8 — Build the Backend APIs
- `GET /news/feed` — personalized news feed with tier + filters
- `GET /news/article/{id}` — full article detail with AI explanation
- `GET /news/filter` — advanced filter endpoint
- `GET /news/reliability/source/{name}` — source reliability stats
- `GET /news/reliability/ticker/{ticker}` — ticker prediction history
- `POST /news/interactions` — track user saves/dismissals

## Step 9 — Build the Filtering System
- Support filters for: impact level, time window, min reliability score, sentiment, sector, source
- Apply filters dynamically via composable SQL query builder
- Cache filtered results in Redis (5–15 min TTL)

## Step 10 — Test Everything
- Unit test: ticker extraction, deduplication, impact score formula
- Integration test: full ingestion → sentiment → reliability pipeline
- Model evaluation: check FinBERT F1 score on FinancialPhraseBank dataset
- Check 30-day backtested directional accuracy (target > 60%)

## Step 11 — Deploy
- Containerize everything with Docker
- Deploy API + Celery workers
- Set up monitoring (error tracking, queue depth alerts, latency dashboards)
- Confirm nightly reliability batch runs and produces accurate scores

---

**Detailed specs for each step → see [`implementationplan.md`](./implementationplan.md) and [`implementationplan_part2.md`](./implementationplan_part2.md)**
