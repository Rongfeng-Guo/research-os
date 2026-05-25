from sqlmodel import Session, select

from .auth import hash_password
from .db import engine
from .models import User
from .settings import settings


def seed_default_user() -> None:
    if settings.app_env != "development":
        return
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == "test@example.com")).first()
        if existing:
            return
        user = User(email="test@example.com", password_hash=hash_password("password123"))
        session.add(user)
        session.commit()
