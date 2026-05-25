import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlmodel import Session

from .db import create_db_and_tables, engine
from .routers import auth, evidence, notes, papers, projects, workspace
from .services.scheduler import start_scheduler, stop_scheduler
from .settings import settings
from .seed import seed_default_user

app = FastAPI(title="Research OS MVP", version="0.1.0")

settings.validate()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s" if settings.log_format != "json" else '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    stream=sys.stdout,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()
    seed_default_user()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.app_env, "database_url": settings.database_url}


@app.get("/health/live")
def health_live():
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready():
    with Session(engine) as session:
        session.exec(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}


app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(papers.router)
app.include_router(evidence.router)
app.include_router(notes.router)
app.include_router(workspace.router)
