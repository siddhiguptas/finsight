from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, insert
from app.core.database import get_db_session
from app.core.auth import get_current_user
from app.models.schemas import UserWatchlist, UserNewsInteraction, NewsArticle
from pydantic import BaseModel

router = APIRouter()

class WatchlistRequest(BaseModel):
    user_id: UUID
    ticker: str

class InteractionRequest(BaseModel):
    user_id: UUID
    article_id: UUID
    interaction: str

@router.post("/watchlist")
async def add_to_watchlist(req: WatchlistRequest, db: AsyncSession = Depends(get_db_session), current_user: dict = Depends(get_current_user)):
    try:
        stmt = insert(UserWatchlist).values(user_id=req.user_id, ticker=req.ticker.upper())
        await db.execute(stmt)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Ticker already in watchlist or invalid data")
    return {"status": "success"}

@router.get("/watchlist/{user_id}")
async def get_watchlist(user_id: UUID, db: AsyncSession = Depends(get_db_session), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(UserWatchlist.ticker).where(UserWatchlist.user_id == user_id))
    return {"tickers": [row[0] for row in result.all()]}

@router.delete("/watchlist")
async def remove_from_watchlist(req: WatchlistRequest, db: AsyncSession = Depends(get_db_session), current_user: dict = Depends(get_current_user)):
    stmt = delete(UserWatchlist).where(UserWatchlist.user_id == req.user_id, UserWatchlist.ticker == req.ticker.upper())
    await db.execute(stmt)
    await db.commit()
    return {"status": "success"}

@router.post("/article")
async def track_interaction(req: InteractionRequest, db: AsyncSession = Depends(get_db_session), current_user: dict = Depends(get_current_user)):
    try:
        stmt = insert(UserNewsInteraction).values(
            user_id=req.user_id, 
            article_id=req.article_id, 
            interaction=req.interaction.lower()
        )
        await db.execute(stmt)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Interaction already exists or invalid article")
    return {"status": "success"}


@router.post("/interactions")
async def track_interaction_alias(req: InteractionRequest, db: AsyncSession = Depends(get_db_session), current_user: dict = Depends(get_current_user)):
    return await track_interaction(req, db, current_user)
