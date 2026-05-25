from __future__ import annotations

import hashlib
import secrets
from typing import Dict, Optional

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session, select

from .db import get_session
from .models import User

TOKEN_STORE: Dict[str, int] = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_token(user_id: int) -> str:
    token = secrets.token_hex(24)
    TOKEN_STORE[token] = user_id
    return token


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    return session.exec(select(User).where(User.email == email)).first()


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.replace("Bearer ", "", 1).strip()
    user_id = TOKEN_STORE.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
