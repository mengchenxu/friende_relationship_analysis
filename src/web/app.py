"""FastAPI application entry point for the relationship analysis tool."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from ..storage import Storage

BASE_DIR = Path(__file__).resolve().parent.parent.parent

app = FastAPI(title="Friend Relationship Analysis")


@app.on_event("startup")
def startup():
    db_path = str(BASE_DIR / "data" / "relation.db")
    app.state.storage = Storage(db_path)
    app.state.storage.init_db()


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head><meta charset="UTF-8"><title>Friend Analysis</title></head>
    <body>
        <h1>👋 Hello World</h1>
        <p>Friend Relationship Analysis is running.</p>
    </body>
    </html>
    """
