# FinSight News Module (Live)

Real-time financial news fetcher with optional ML analysis. This version removes the multi-DB pipeline and returns fresh, ticker-focused results on each request.

## What This Service Does

- Fetches live news for a list of tickers from configured sources.
- Deduplicates results in-memory and filters by a time window.
- Optionally runs FinBERT sentiment + impact scoring (and Gemini explanation if configured).

## API Endpoints

### Health
`GET /health`

### Live Feed
`POST /api/v1/news/feed`

**Request Body**
```json
{
  "tickers": ["AAPL", "MSFT"],
  "company_names": ["Apple", "Microsoft"],
  "market": "US",
  "time_window_hours": 24,
  "limit": 20,
  "sources": ["newsapi", "yahoo_rss", "google_news_rss"],
  "analysis_mode": "fast",
  "explanation_detail": "medium",
  "explanation_format": "paragraph"
}
```

**Response**
```json
{
  "count": 2,
  "articles": [
    {
      "id": "hash",
      "title": "Apple posts strong quarterly results",
      "source_name": "Reuters",
      "source_url": "https://...",
      "published_at": "2026-03-19T10:12:00Z",
      "summary": "Apple reported...",
      "image_url": "https://...",
      "tickers": ["AAPL"],
      "sentiment_label": "POSITIVE",
      "sentiment_score": 0.83,
      "impact_level": "HIGH",
      "impact_score": 0.78,
      "ai_explanation": "..."
    }
  ]
}
```

### Analyze One Article
`POST /api/v1/news/analyze`

**Request Body**
```json
{
  "title": "Apple announces new product line",
  "content": "Apple today announced...",
  "ticker": "AAPL",
  "analysis_mode": "full",
  "explanation_detail": "detailed",
  "explanation_format": "bullets"
}
```

## Configuration

Create a `.env` file from the example:
```bash
copy .env.example .env
```

Required variables:
- `NEWSAPI_KEY` (optional but recommended; RSS sources work without it)
- `GEMINI_API_KEY` (optional; only used for `analysis_mode=full`)
- `GEMINI_RPM` (optional; default `4` to stay under free-tier rate limits)
- `LOG_LEVEL` (optional)

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "from transformers import pipeline; pipeline('text-classification', model='ProsusAI/finbert')"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Notes

- Default sources: `newsapi`, `yahoo_rss`, `google_news_rss`.
- `analysis_mode`:
  - `none`: no ML analysis
  - `fast`: FinBERT sentiment + impact
  - `full`: FinBERT + Gemini explanation (if key set)
- `explanation_detail`: `short` | `medium` | `detailed`
- `explanation_format`: `paragraph` | `bullets`
- Deduplication is per-response to remove cross-source duplicates while still returning results on repeated requests.
- First-time `analysis_mode=fast/full` may be slow unless FinBERT is pre-downloaded using the command above.
- Gemini free-tier quotas are low (e.g., ~5 requests/minute). The UI feed uses `analysis_mode=fast` to avoid hitting limits. Use per-item **Analyze** or `/api/v1/news/analyze` for full Gemini explanations.
