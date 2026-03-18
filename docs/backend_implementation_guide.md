# Backend Engineer's Implementation Guide

This guide describes how the ML modules fit together in the FinSight News backend and how to implement/extend them.

## 1. Overview of the AI/ML Architecture
The core logic resides in `app.processing`. The architecture utilizes a layered pipeline:
1. **Entity Recognition (NER):** Uses `spaCy` (en_core_web_lg) to extract organizations and map them to known tickers in the S&P 500 via the `TickerSectorMap` database table. Finds primary ticker.
2. **Sentiment Analysis:** Uses `FinBERT` (via Hugging Face Transformers) to determine POSITIVE, NEUTRAL, or NEGATIVE sentiment and score.
3. **Impact Scoring:** A mathematical formula combining FinBERT score, keyword urgency, and source credibility.
4. **AI Summarization:** Uses `Gemini 1.5 Flash` to generate a 2-sentence market impact justification.

## 2. Using the Models in Tasks / Endpoints

### Initializing the Models
The models (`spacy` and `FinBERT`) are initialized globally at the module level when the file is imported. This is beneficial for worker processes as it avoids reloading models for every request.
* **Important:** If you run this within an ASGI server (like Uvicorn/FastAPI with multiple workers), the models will consume memory per worker. For background jobs, Celery workers will initialize them on startup.

### Integration Flow Example
When a new article is ingested, you can orchestrate the processing sequentially:

```python
from app.processing.nlp_pipeline import extract_tickers_from_article, classify_sector_by_keywords
from app.processing.sentiment_engine import classify_sentiment, compute_impact_score, generate_explanation

async def process_article(title: str, content: str, source_trust_score: float = 0.5):
    # 1. Extract Tickers
    tickers = await extract_tickers_from_article(title, content)
    if not tickers:
        # Fallback to sector classification if no tickers exist
        sector = await classify_sector_by_keywords(title, content)
        return {"sector": sector, "tickers": []}
    
    primary_ticker_data = next((t for t in tickers if t['is_primary']), tickers[0])
    ticker_symbol = primary_ticker_data['ticker']
    
    # 2. Extract Sentiment
    sentiment_data = await classify_sentiment(title + " " + content)
    
    # 3. Calculate Impact Score
    impact_score, impact_level = await compute_impact_score(
        sentiment_score=sentiment_data['score'], 
        title=title, 
        is_primary=primary_ticker_data['is_primary'],
        source_credibility=source_trust_score
    )
    
    # 4. Generate AI Explanation
    explanation = await generate_explanation(
        title=title,
        content=content,
        ticker=ticker_symbol,
        sentiment=sentiment_data['label']
    )
    
    # Return processed intelligence
    return {
        "primary_ticker": ticker_symbol,
        "sentiment": sentiment_data['label'],
        "impact_score": impact_score,
        "impact_level": impact_level,
        "explanation": explanation
    }
```

## 3. Scaling & Performance Considerations
- **Hardware Acceleration:** Currently, FinBERT in `sentiment_engine.py` is configured with `device=-1` (CPU). For higher throughput via GPU acceleration, set `device=0` if cuda/pytorch is available and enabled on the environment.
- **API Limits:** Gemini calls use the Tenacity backoff/retry decorator to gracefully handle 429 warnings and temporary API failures. Do not remove this decorator without replacing it with an external queue delay.
- **Memory Footprint:** 
  - The `en_core_web_lg` spaCy model requires about ~800MB of RAM. 
  - `FinBERT` also requires ~450MB of RAM. 
  - Adjust Celery concurrency based on total memory available so OOM (Out Of Memory) issues do not happen in production.
