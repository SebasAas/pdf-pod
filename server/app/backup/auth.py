import os
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.hash import bcrypt
from sqlmodel import select
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .db import User, get_session

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_me")
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "4320"))
security = HTTPBearer()

def hash_password(p: str) -> str:
    return bcrypt.hash(p)

def verify_password(p: str, hashed: str) -> bool:
    return bcrypt.verify(p, hashed)

def create_token(user_id: int) -> str:
    exp = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MIN)
    return jwt.encode({"sub": str(user_id), "exp": exp}, JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> Optional[int]:
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return int(data["sub"])
    except JWTError:
        return None

def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(security)) -> int:
    user_id = decode_token(creds.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id
