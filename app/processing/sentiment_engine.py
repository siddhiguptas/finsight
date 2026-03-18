import google.generativeai as genai
from transformers import pipeline
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

_finbert = None
_gemini_model = None


def get_finbert():
    """Lazy-load FinBERT to avoid startup delays or download attempts."""
    global _finbert
    if _finbert is None:
        _finbert = pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
            device=-1,  # CPU, use 0 for GPU
            return_all_scores=True,
            max_length=512,
            truncation=True,
        )
    return _finbert


def get_gemini_model():
    """Lazy-init Gemini client when needed."""
    global _gemini_model
    if _gemini_model is None and settings.gemini_api_key:
        genai.configure(api_key=settings.gemini_api_key)
        _gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    return _gemini_model

async def classify_sentiment(text: str):
    """Run FinBERT for sentiment classification."""
    finbert = get_finbert()
    results = finbert(text[:3000])[0]
    scores = {res['label'].upper(): res['score'] for res in results}
    label = max(scores, key=scores.get)
    return {
        "label": label,
        "score": scores[label],
        "positive": scores.get("POSITIVE", 0),
        "neutral": scores.get("NEUTRAL", 0),
        "negative": scores.get("NEGATIVE", 0)
    }

async def compute_impact_score(sentiment_score: float, title: str, is_primary: bool, source_credibility: float = 0.5):
    """
    Day 4 Advancement: Advanced Weighted Impact Scoring.
    Combines sentiment strength, keyword urgency, ticker priority, and source credibility.
    """
    # Expanded High-impact keywords with weights
    CRITICAL_KEYWORDS = ["bankruptcy", "fraud", "ceo", "acquisition", "merger", "earnings", "guidance"]
    URGENT_KEYWORDS = ["fda", "lawsuit", "layoff", "dividend", "rating", "sec"]
    
    title_lower = title.lower()
    
    keyword_score = 0.0
    if any(kw in title_lower for kw in CRITICAL_KEYWORDS):
        keyword_score = 0.4
    elif any(kw in title_lower for kw in URGENT_KEYWORDS):
        keyword_score = 0.2
        
    sentiment_strength = abs(sentiment_score - 0.5) * 2
    primary_weight = 0.2 if is_primary else 0.05
    
    # Advanced Weighted Formula
    # 30% Sentiment, 30% Keywords, 20% Source Trust, 20% Ticker Relevance
    raw_score = (
        (0.3 * sentiment_strength) + 
        (0.3 * keyword_score) + 
        (0.2 * source_credibility) + 
        (0.2 * primary_weight)
    )
    
    impact_score = min(1.0, raw_score * 2.0) # Normalized
    
    if impact_score >= 0.75:
        level = "HIGH"
    elif impact_score >= 0.4:
        level = "MEDIUM"
    else:
        level = "LOW"
        
    return impact_score, level


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def generate_explanation(title: str, content: str, ticker: str, sentiment: str):
    """Generate 2-sentence impact explanation using Gemini."""
    model = get_gemini_model()
    if not model:
        return f"Sentiment for {ticker} is {sentiment.lower()} based on current market data."
    
    prompt = f"""
    You are a senior financial analyst. Explain in 2 concise sentences how this news impacts {ticker}.
    Article Title: {title}
    Content Summary: {content[:300]}
    Predicted Sentiment: {sentiment}

    Guidelines: Be factual, quantify impact where possible, and do not recommend any action.
    """
    
    response = await model.generate_content_async(
        prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=200,
            temperature=0.2,
        )
    )
    return response.text.strip()
