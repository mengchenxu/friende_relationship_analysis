"""FastAPI application entry point for the relationship analysis tool."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from ..storage import Storage
from .routes import router

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@asynccontextmanager
async def lifespan(application: FastAPI):
    db_path = str(BASE_DIR / "data" / "relation.db")
    application.state.storage = Storage(db_path)
    application.state.storage.init_db()
    yield
    application.state.storage.close()


app = FastAPI(title="Friend Relationship Analysis", lifespan=lifespan)
app.include_router(router)
