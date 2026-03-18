from uuid import UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.auth import auth_middleware

router = APIRouter()

class TokenRequest(BaseModel):
    user_id: UUID
    role: str = "student"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str

@router.post("/token", response_model=TokenResponse)
async def generate_token(req: TokenRequest):
    token = auth_middleware.create_access_token(str(req.user_id), req.role)
    return TokenResponse(
        access_token=token,
        user_id=str(req.user_id),
        role=req.role
    )
