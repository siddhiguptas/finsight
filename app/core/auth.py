from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

ALGORITHM = "HS256"

class AuthMiddleware:
    def __init__(self):
        self.secret_key = settings.secret_key or "default_secret_key"

    async def verify_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            role: str = payload.get("role", "student")

            if user_id is None:
                return None

            return {"user_id": user_id, "role": role}
        except JWTError:
            return None

    def create_access_token(self, user_id: str, role: str = "student") -> str:
        to_encode = {"sub": user_id, "role": role}
        return jwt.encode(to_encode, self.secret_key, algorithm=ALGORITHM)

auth_middleware = AuthMiddleware()

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = await auth_middleware.verify_token(token)
    if payload is None:
        raise credentials_exception

    return payload
