import re
from typing import Optional

import spacy
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.schemas import TickerSectorMap

_nlp: Optional["spacy.language.Language"] = None


def get_nlp():
    """
    Lazy-load spaCy model to avoid startup failures.
    Prefer large model, fall back to small; if neither exists, return None.
    """
    global _nlp
    if _nlp is not None:
        return _nlp

    for model_name in ("en_core_web_lg", "en_core_web_sm"):
        try:
            _nlp = spacy.load(model_name)
            return _nlp
        except OSError:
            continue

    _nlp = None
    return None

async def extract_tickers_from_article(title: str, content: str):
    """
    Extracts stock tickers from title and content using regex and spaCy NER.
    Returns: List of dicts {ticker, company_name, mention_count, is_primary, confidence}
    """
    full_text = f"{title}. {content}"
    nlp = get_nlp()
    doc = nlp(full_text) if nlp else None
    
    # 1. Regex search for potential tickers (1-5 uppercase letters)
    ticker_candidates = re.findall(r'\b[A-Z]{1,5}\b', full_text)
    
    # 2. Get valid tickers from ticker_sector_map
    async with AsyncSessionLocal() as session:
        stmt = select(TickerSectorMap)
        result = await session.execute(stmt)
        valid_tickers = {r.ticker: r.company_name for r in result.scalars()}
    
    found_tickers = {}
    
    # Check regex matches
    for candidate in ticker_candidates:
        if candidate in valid_tickers:
            found_tickers[candidate] = found_tickers.get(candidate, 0) + 1
            
    # 3. Use spaCy NER for organization names
    if doc:
        for ent in doc.ents:
            if ent.label_ == "ORG":
                # Simple reverse lookup: company name -> ticker
                for ticker, name in valid_tickers.items():
                    if name.lower() in ent.text.lower() or ent.text.lower() in name.lower():
                        found_tickers[ticker] = found_tickers.get(ticker, 0) + 1
                        break
                    
    if not found_tickers:
        return []
        
    # Determine primary ticker: most mentions, and weighted towards title
    title_tickers = re.findall(r'\b[A-Z]{1,5}\b', title)
    for ticker in title_tickers:
        if ticker in found_tickers:
            found_tickers[ticker] += 2 # Boost title mentions
            
    primary_ticker = max(found_tickers, key=found_tickers.get)
    
    results = []
    for ticker, count in found_tickers.items():
        results.append({
            "ticker": ticker,
            "company_name": valid_tickers[ticker],
            "mention_count": count,
            "is_primary": (ticker == primary_ticker),
            "confidence": 0.8 if ticker in title_tickers else 0.6
        })
        
    return results

async def classify_sector_by_keywords(title: str, content: str):
    """Fallback sector classification based on keywords."""
    combined = (title + " " + content).lower()
    
    SECTOR_KEYWORDS = {
        "Technology": ["software", "ai", "cloud", "semiconductor", "chip", "digital", "app"],
        "Healthcare": ["fda", "drug", "pharma", "biotech", "clinical", "hospital", "vaccine"],
        "Finance": ["bank", "fed", "interest", "loan", "mortgage", "fintech", "payment"],
        "Energy": ["oil", "gas", "crude", "solar", "wind", "renewable", "energy"],
        "Consumer": ["retail", "ecommerce", "spending", "shopping", "logistics"]
    }
    
    scores = {sector: 0 for sector in SECTOR_KEYWORDS}
    for sector, kws in SECTOR_KEYWORDS.items():
        for kw in kws:
            if kw in combined:
                scores[sector] += 1
                
    best_sector = max(scores, key=scores.get)
    return best_sector if scores[best_sector] > 0 else "General Market"
