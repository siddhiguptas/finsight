import asyncio
from datetime import datetime
from celery import shared_task
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.core.mongodb import mongo_db
from app.models.schemas import NewsArticle, NewsStockTag, NewsSectorTag, NewsSentimentAnalysis, TickerSectorMap
from app.processing.nlp_pipeline import extract_tickers_from_article, classify_sector_by_keywords
from app.processing.sentiment_engine import classify_sentiment, compute_impact_score, generate_explanation
from app.core.redis import redis_client

@shared_task(name="app.tasks.process.process_article")
def process_article(article_id: str):
    try:
        from gevent import spawn
        spawn(lambda: asyncio.run(_run())).join()
    except ImportError:
        asyncio.run(_run())
    return {"status": "done"}

async def _run():
    async with AsyncSessionLocal() as session:
        stmt = select(NewsArticle).where(NewsArticle.id == article_id)
        result = await session.execute(stmt)
        article = result.scalar_one_or_none()
        
        if not article:
            return {"status": "error", "message": "Article not found"}
        
        from bson import ObjectId
        mongo_art = await mongo_db.raw_articles.find_one({"_id": ObjectId(article.full_text_ref)})
        if not mongo_art:
            return {"status": "error", "message": "Raw content not found"}
        
        content = mongo_art.get("full_text", "")
        
        ticker_tags = await extract_tickers_from_article(article.title, content)
        
        primary_ticker = None
        for tag in ticker_tags:
            new_tag = NewsStockTag(
                article_id=article_id,
                ticker=tag["ticker"],
                company_name=tag["company_name"],
                is_primary=tag["is_primary"],
                mention_count=tag["mention_count"],
                confidence=tag["confidence"]
            )
            session.add(new_tag)
            if tag["is_primary"]:
                primary_ticker = tag["ticker"]
                
        if ticker_tags:
            tickers = [t["ticker"] for t in ticker_tags]
            sec_stmt = select(TickerSectorMap).where(TickerSectorMap.ticker.in_(tickers))
            sec_res = await session.execute(sec_stmt)
            for sector_map in sec_res.scalars():
                new_sec_tag = NewsSectorTag(
                    article_id=article_id,
                    sector_name=sector_map.sector,
                    is_primary=(primary_ticker == sector_map.ticker)
                )
                session.add(new_sec_tag)
        else:
            best_sector = await classify_sector_by_keywords(article.title, content)
            new_sec_tag = NewsSectorTag(
                article_id=article_id,
                sector_name=best_sector,
                is_primary=True
            )
            session.add(new_sec_tag)
        
        await session.commit()
        analyze_sentiment.delay(article_id)

@shared_task(name="app.tasks.process.analyze_sentiment")
def analyze_sentiment(article_id: str):
    from gevent import spawn
    spawn(lambda: asyncio.run(_run())).join()
    return {"status": "done"}

async def _run():
    async with AsyncSessionLocal() as session:
        from app.models.schemas import SourceReliabilityStats
        stmt = select(NewsArticle).where(NewsArticle.id == article_id)
        result = await session.execute(stmt)
        article = result.scalar_one_or_none()
        if not article: return
        
        cred_stmt = select(SourceReliabilityStats.accuracy_24h).where(
            SourceReliabilityStats.source_name == article.source_name
        )
        cred_res = await session.execute(cred_stmt)
        source_credibility = cred_res.scalar() or 0.5
        
        tags_stmt = select(NewsStockTag).where(NewsStockTag.article_id == article_id)
        tags_res = await session.execute(tags_stmt)
        tags = tags_res.scalars().all()
        
        from bson import ObjectId
        mongo_art = await mongo_db.raw_articles.find_one({"_id": ObjectId(article.full_text_ref)})
        content = mongo_art.get("full_text", "")
        
        global_sentiment = await classify_sentiment(content)
        
        for tag in tags:
            impact_score, impact_level = await compute_impact_score(
                global_sentiment["score"], 
                article.title, 
                tag.is_primary, 
                source_credibility
            )
            
            if impact_level in ["HIGH", "MEDIUM"] or tag.is_primary:
                ai_exp = await generate_explanation(
                    article.title, 
                    content, 
                    tag.ticker, 
                    global_sentiment["label"]
                )
                
                analysis = NewsSentimentAnalysis(
                    article_id=article_id,
                    ticker=tag.ticker,
                    sentiment_label=global_sentiment["label"],
                    sentiment_score=global_sentiment["score"],
                    positive_score=global_sentiment["positive"],
                    neutral_score=global_sentiment["neutral"],
                    negative_score=global_sentiment["negative"],
                    impact_level=impact_level,
                    impact_score=impact_score,
                    ai_explanation=ai_exp,
                    ai_model_used="finbert-gemini-v1-adv"
                )
                session.add(analysis)
                
                await redis_client.delete(f"reliability:ticker:{tag.ticker}")

        if not tags:
             impact_score, impact_level = await compute_impact_score(global_sentiment["score"], article.title, False, source_credibility)
             analysis = NewsSentimentAnalysis(
                    article_id=article_id,
                    ticker="MARKET",
                    sentiment_label=global_sentiment["label"],
                    sentiment_score=global_sentiment["score"],
                    impact_level=impact_level,
                    impact_score=impact_score,
                    ai_explanation=f"General market impact: {global_sentiment['label']}",
                    ai_model_used="finbert-gemini-v1-adv"
             )
             session.add(analysis)

        await session.execute(
            update(NewsArticle).where(NewsArticle.id == article_id).values(processed_at=datetime.utcnow())
        )
        await session.commit()

