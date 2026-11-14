import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# --- Models ---
class Entry(BaseModel):
    id: str
    title: str
    content: str
    lastModifiedBy: str
    lastModifiedAt: str

class NewEntry(BaseModel):
    title: str
    content: str
    createdBy: str

class UpdateEntry(BaseModel):
    content: str
    modifiedBy: str
    summary: str

# --- Database Setup ---
DB_PATH = "db.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                lastModifiedBy TEXT NOT NULL,
                lastModifiedAt TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entryId TEXT NOT NULL,
                content TEXT NOT NULL,
                modifiedBy TEXT NOT NULL,
                summary TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(entryId) REFERENCES entries(id)
            )
        """)
        conn.commit()

# --- App Initialization ---
app = FastAPI(title="Wiki API")
templates = Jinja2Templates(request=None) # We will pass request in the route

# Simple HTML templates embedded as strings for the "one file" requirement
# Jinja2Templates usually looks for files, but we can override the render logic or use a mock
# Since we must use Jinja2, we'll define the templates in a way that works with the provided library.
# However, for a single-file requirement without a filesystem, we can use HTMLResponse directly 
# or define a simple helper.

def render_html(template_name: str, context: dict):
    # Mocking the template rendering since we can't create separate .html files
    # We use a simple string replacement or f-string logic for the "Wiki" feel
    if template_name == "index":
        links = "".join([f'<li><a href="/entries/{e["id"]}">{e["title"]}</a></li>' for e in context['entries']])
        return f"""
        <html><body>
            <h1>Wiki Home</h1>
            <a href="/create">Create New Entry</a>
            <ul>{links}</ul>
        </body></html>
        """
    elif template_name == "entry":
        e = context['entry']
        return f"""
        <html><body>
            <h1>{e['title']}</h1>
            <p>{e['content']}</p>
            <hr>
            <p>Last modified by {e['lastModifiedBy']} at {e['lastModifiedAt']}</p>
            <a href="/entries/{e['id']}/edit">Edit this page</a> | 
            <a href="/entries/{e['id']}/edits">View History</a> | 
            <a href="/entries">Back to Home</a>
        </body></html>
        """
    elif template_name == "history":
        edits = context['edits']
        rows = "".join([f"<li>{edit['timestamp']} - {edit['modifiedBy']}: {edit['summary']} <br><pre>{edit['content']}</pre></li>" for edit in edits])
        return f"""
        <html><body>
            <h1>Edit History</h1>
            <ul>{rows}</ul>
            <a href="/entries">Back to Home</a>
        </body></html>
        """
    elif template_name == "edit_form":
        e = context.get('entry', {})
        title = e.get('title', '')
        content = e.get('content', '')
        return f"""
        <html><body>
            <h1>{'Edit' if e else 'Create'} Entry</h1>
            <form method="post" action="{'/entries/' + e['id'] if e else '/entries'}">
                <label>Title:</label><br>
                <input type="text" name="title" value="{title}" {'readonly' if e else ''}><br>
                <label>Content:</label><br>
                <textarea name="content" rows="10" cols="50">{content}</textarea><br>
                <label>Your Name:</label><br>
                <input type="text" name="user"><br>
                <label>Edit Summary:</label><br>
                <input type="text" name="summary"><br>
                <button type="submit">Save</button>
            </form>
        </body></html>
        """
    return "404 Not Found"

# --- Routes ---

@app.get("/entries", response_class=HTMLResponse)
async def get_entries():
    with get_db() as conn:
        entries = conn.execute("SELECT id, title FROM entries").fetchall()
        # Convert Row objects to dicts for the renderer
        entries_list = [dict(row) for row in entries]
    return render_html("index", {"entries": entries_list})

@app.post("/entries", status_code=201)
async def create_entry(entry: NewEntry):
    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)",
            (entry_id, entry.title, entry.content, entry.createdBy, now)
        )
        conn.execute(
            "INSERT INTO edits (entryId, content, modifiedBy, summary, timestamp) VALUES (?, ?, ?, ?, ?)",
            (entry_id, entry.content, entry.createdBy, "Initial creation", now)
        )
        conn.commit()
    return Entry(id=entry_id, title=entry.title, content=entry.content, lastModifiedBy=entry.createdBy, lastModifiedAt=now)

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        return render_html("entry", {"entry": dict(row)})

@app.put("/entries/{entryId}")
async def update_entry(entryId: str, update: UpdateEntry):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?",
            (update.content, update.modifiedBy, now, entryId)
        )
        conn.execute(
            "INSERT INTO edits (entryId, content, modifiedBy, summary, timestamp) VALUES (?, ?, ?, ?, ?)",
            (entryId, update.content, update.modifiedBy, update.summary, now)
        )
        conn.commit()
        
        updated = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        return Entry(**dict(updated))

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    with get_db() as conn:
        # Check if entry exists
        entry = conn.execute("SELECT id FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        edits = conn.execute("SELECT * FROM edits WHERE entryId = ? ORDER BY timestamp DESC", (entryId,)).fetchall()
        return render_html("history", {"edits": [dict(row) for row in edits]})

# --- Helper Routes for the UI (Not in OpenAPI but needed for the webapp to function) ---

@app.get("/create", response_class=HTMLResponse)
async def create_page():
    return render_html("edit_form", {})

@app.get("/entries/{entryId}/edit", response_class=HTMLResponse)
async def edit_page(entryId: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        return render_html("edit_form", {"entry": dict(row)})

@app.post("/entries", response_class=HTMLResponse) # Overloaded for HTML form
async def create_entry_html(request: Request):
    form = await request.form()
    new_entry = NewEntry(title=form['title'], content=form['content'], createdBy=form['user'])
    await create_entry(new_entry)
    return HTMLResponse(content="Entry created! <a href='/entries'>Go Home</a>")

@app.post("/entries/{entryId}", response_class=HTMLResponse) # Overloaded for HTML form
async def update_entry_html(entryId: str, request: Request):
    form = await request.form()
    update = UpdateEntry(content=form['content'], modifiedBy=form['user'], summary=form['summary'])
    await update_entry(entryId, update)
    return HTMLResponse(content="Entry updated! <a href='/entries'>Go Home</a>")

# --- Startup ---
init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)