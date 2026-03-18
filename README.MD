# FinSight News Module 🚀

Intelligent News Aggregation & Analysis System for FinSight.

## ✅ Sprint Status: ALL PHASES COMPLETE (MVP + Advancements)

The 5-day sprint is finished. The system is now a fully automated intelligence pipeline.

### Core Features:
- **Phase 1 (Ingestion)**: Multi-source fetching from NewsAPI, RSS (Yahoo/Google), and Reddit.
- **Phase 2 (NLP & Tagging)**: Automatic ticker extraction (spaCy NER) and Sector/Industry mapping.
- **Phase 3 (AI Analysis)**: Sentiment classification (FinBERT) and Impact justifications (Gemini AI).
- **Phase 4 (Reliability)**: Automatic backtesting. The system checks predicted sentiment against real 24h stock price moves (yfinance).
- **Phase 5 (Personalization)**: Per-user news feeds based on custom watchlists and sector interests.
- **Phase 6 (APIs)**: High-performance FastAPI endpoints for feeds, searches, and analysis details.

---

## 🛠️ Architecture & Workflow

1. **Ingest**: Celery Beat triggers periodic pulls from NewsAPI, RSS, and Reddit.
2. **Deduplicate**: Redis-based hashing prevents processing the same story twice.
3. **Analyze**: 
   - **FinBERT** determines the market sentiment.
   - **Gemini AI** writes a 2-sentence impact explanation.
   - **Weighted Impact Score** factors in source credibility and critical keywords.
4. **Relate**: Tickers are mapped to their S&P 500 sectors for industry-level news grouping.
5. **Backtest**: 24 hours later, the system automatically compares our prediction with market reality to score the source's reliability.

---

## 🚀 Getting Started

### 1. Environment Set Up
Ensure your `.env` is populated with keys for Neon (Postgres), Atlas (MongoDB), and Upstash (Redis).

### 2. Docker Execution (Production Mode)
```bash
docker-compose build
docker-compose up -d
```
This starts the **API**, the **Celery Worker**, and the **Celery Beat** dispatcher.

### 3. Verification
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: `GET /health`

---

## 📂 Project Structure
- `app/api/`: FastAPI route definitions.
- `app/processing/`: Core NLP, Sentiment, and Impact engines.
- `app/tasks/`: Celery task definitions (ingest, process, reliability).
- `app/ingestion/`: API clients for news sources.
- `app/models/`: Databases schemas and API request/response models.
- `scripts/`: Maintenance scripts (e.g., seeding S&P 500 data).
