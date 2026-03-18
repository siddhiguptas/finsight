# Model Testing Guide

This guide details how to unit test and integrate the ML components of the FinSight News processing pipeline.

## 1. Prerequisites
Ensure you have the required dependencies installed:
- `spacy` and the en_core_web_lg model
- `transformers` and `torch`
- `google-generativeai`
- `pytest`
- `pytest-asyncio`

## 2. Testing the NLP Pipeline (`app.processing.nlp_pipeline`)

### Ticker Extraction (`extract_tickers_from_article`)
This function relies on `spaCy` NER and database validation.
- **Mocking the DB:** Since the function calls `AsyncSessionLocal`, mock the database session to return predefined `TickerSectorMap` objects (e.g., using `unittest.mock.patch` on `AsyncSessionLocal`).
- **Test Scenarios:**
  - Standard text with known company names (e.g., "Apple announced new earnings.").
  - Tickers in all caps directly (e.g., "AAPL earnings call...").
  - Texts without any tickers to ensure robust fallback (should return `[]`).
  - Ensuring the primary ticker is correctly identified based on title/mentions prioritizing title mentions.

### Classification (`classify_sector_by_keywords`)
- **Action:** Unit test the dictionary keyword matcher with pure, deterministic inputs.
- **Example:** Test case with string "tech cloud software" should return "Technology".
- **Default:** "General Market" should be returned if no keywords match.

## 3. Testing the Sentiment Engine (`app.processing.sentiment_engine`)

### FinBERT Sentiment (`classify_sentiment`)
- **Action:** FinBERT runs asynchronously wrapped but utilizes the `transformers` pipeline synchronously under the hood. For true unit testing, mock the `finbert` pipeline object to return predefined scores.
- **Test Scenarios:**
  - Positive text ("Earnings soared to record highs.") -> Expect POSITIVE label with high score.
  - Negative text ("Company faces bankruptcy and lawsuit.") -> Expect NEGATIVE label.
  - Neutral text ("The company held a meeting.") -> Expect NEUTRAL.

### Impact Scoring (`compute_impact_score`)
This is a purely deterministic function. You can unit test this without any ML models loaded.
- Ensure combinations of `sentiment_score`, `is_primary`, and keywords in the title properly map to LOW, MEDIUM, and HIGH impact levels.
- Example: Title containing "bankruptcy" should heavily boost the impact score.

### Gemini Justification (`generate_explanation`)
- **Action:** Mock the `genai.GenerativeModel.generate_content_async` call to prevent live API requests during CI/CD.
- **Resilience:** Ensure the retry logic (via `@retry` from Tenacity) is functional by mimicking rate limits or timeouts in your mock, ensuring it stops after 3 attempts.
