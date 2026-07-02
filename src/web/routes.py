"""Web routes for the relationship analysis application."""

import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..adapters.testdata import TestDataAdapter
from ..models import Sender

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMPORTS_DIR = BASE_DIR / "data" / "imports"


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    storage = request.app.state.storage
    contacts = storage.list_contacts()

    rows = ""
    for c in contacts:
        conv = storage.get_conversation_by_contact(c.id)
        msg_count = conv.message_count if conv else 0
        last_active = ""
        if conv and conv.last_msg_time:
            last_active = conv.last_msg_time.strftime("%Y-%m-%d %H:%M")

        rows += f"""
        <tr>
            <td><a href="/contact/{c.id}">{c.name}</a></td>
            <td>{c.platform}</td>
            <td>{msg_count}</td>
            <td>{last_active}</td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="4">No contacts imported yet.</td></tr>'

    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>Friend Relationship Analysis</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
            table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
            th, td {{ text-align: left; padding: 0.75rem; border-bottom: 1px solid #e0e0e0; }}
            th {{ background: #f5f5f5; }}
            a {{ color: #2563eb; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .import-btn {{ display: inline-block; padding: 0.5rem 1.5rem; background: #2563eb; color: white; border-radius: 4px; margin: 1rem 0; }}
            .import-btn:hover {{ background: #1d4ed8; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>👥 Friend Relationship Analysis</h1>
        <p><a href="/import" class="import-btn">Import Chat Data</a></p>
        <table>
            <thead>
                <tr><th>Contact</th><th>Platform</th><th>Messages</th><th>Last Active</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </body>
    </html>
    """


@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request):
    """Show available import files and trigger import."""
    storage = request.app.state.storage
    files = sorted(IMPORTS_DIR.glob("*.json")) if IMPORTS_DIR.exists() else []
    adapter = TestDataAdapter()

    results = []
    for fp in files:
        try:
            contacts, messages, platform = adapter.parse(str(fp))
            for contact in contacts:
                c = storage.get_or_create_contact(contact.name, contact.platform)
                conv = storage.get_or_create_conversation(c.id)
                for m in messages:
                    m.conversation_id = conv.id
                inserted = storage.bulk_insert_messages(messages)
                storage.update_conversation_stats(conv.id)
                results.append((fp.name, "ok", f"{len(messages)} messages"))
        except Exception as e:
            results.append((fp.name, "fail", str(e)))

    result_html = ""
    for name, status, detail in results:
        result_html += f'<tr><td>{name}</td><td style="color: {"green" if status == "ok" else "red"}">{status}</td><td>{detail}</td></tr>'

    if not result_html:
        result_html = '<tr><td colspan="3">No import files found in data/imports/</td></tr>'

    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>Import - Friend Analysis</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
            table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
            th, td {{ text-align: left; padding: 0.75rem; border-bottom: 1px solid #e0e0e0; }}
            th {{ background: #f5f5f5; }}
            a {{ color: #2563eb; }}
        </style>
    </head>
    <body>
        <h1>📥 Import Chat Data</h1>
        <table>
            <thead><tr><th>File</th><th>Status</th><th>Detail</th></tr></thead>
            <tbody>{result_html}</tbody>
        </table>
        <p><a href="/">← Back to Contacts</a></p>
    </body>
    </html>
    """


@router.get("/contact/{contact_id}", response_class=HTMLResponse)
def contact_detail(contact_id: int, request: Request):
    """Detail page for a single contact — placeholder for Slice 3."""
    storage = request.app.state.storage
    contact = storage.get_contact(contact_id)
    if not contact:
        return HTMLResponse("<h1>Contact not found</h1>", status_code=404)

    conv = storage.get_conversation_by_contact(contact_id)
    msg_count = conv.message_count if conv else 0

    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>{contact.name} - Friend Analysis</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
            a {{ color: #2563eb; }}
        </style>
    </head>
    <body>
        <h1>{contact.name}</h1>
        <p>Platform: {contact.platform}</p>
        <p>Messages: {msg_count}</p>
        <p>Analysis coming in Slice 3 & 4.</p>
        <p><a href="/">← Back to Contacts</a></p>
    </body>
    </html>
    """
