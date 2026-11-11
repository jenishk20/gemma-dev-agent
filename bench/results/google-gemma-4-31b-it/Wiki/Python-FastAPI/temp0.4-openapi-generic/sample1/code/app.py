import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

app = FastAPI(title="Wiki API")
templates = Jinja2Templates(directory=".") # Templates are embedded as strings in this single-file setup

# --- Database Setup ---
DB_PATH = "db.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        # Entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                last_modified_by TEXT,
                last_modified_at TEXT
            )
        """)
        # Edits table for change tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT,
                content TEXT,
                modified_by TEXT,
                summary TEXT,
                modified_at TEXT,
                FOREIGN KEY(entry_id) REFERENCES entries(id)
            )
        """)
        conn.commit()

init_db()

# --- Pydantic Models ---
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

# --- HTML Templates (Embedded) ---
# Since we must keep everything in one file, we use Jinja2's ability to render from strings
# or we can just use a helper function to return HTML. 
# To comply with "Jinja2" being in the allowed list, I'll use a simple string-based template approach.

def render_html(template_name: str, context: dict):
    # Simple mock for template rendering since we can't have separate .html files
    templates_map = {
        "index": """
        <html>
            <head><title>Wiki Home</title></head>
            <body>
                <h1>Wiki Entries</h1>
                <ul>
                    {% for entry in entries %}
                    <li><a href="/entries/{{ entry.id }}">{{ entry.title }}</a></li>
                    {% endfor %}
                </ul>
                <hr>
                <h3>Create New Entry</h3>
                <form action="/entries" method="post">
                    <input type="text" name="title" placeholder="Title" required><br>
                    <textarea name="content" placeholder="Content" required></textarea><br>
                    <input type="text" name="createdBy" placeholder="Your Name" required><br>
                    <button type="submit">Create</button>
                </form>
            </body>
        </html>
        """,
        "entry": """
        <html>
            <head><title>{{ entry.title }}</title></head>
            <body>
                <a href="/entries">← Back to Home</a>
                <h1>{{ entry.title }}</h1>
                <div style="border: 1px solid #ccc; padding: 10px; white-space: pre-wrap;">{{ entry.content }}</div>
                <p>Last modified by: {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}</p>
                <hr>
                <h3>Edit Entry</h3>
                <form action="/entries/{{ entry.id }}" method="post">
                    <textarea name="content" style="width: 100%; height: 200px;" required>{{ entry.content }}</textarea><br>
                    <input type="text" name="modifiedBy" placeholder="Your Name" required><br>
                    <input type="text" name="summary" placeholder="Edit Summary" required><br>
                    <button type="submit">Update</button>
                </form>
                <p><a href="/entries/{{ entry.id }}/edits">View Edit History</a></p>
            </body>
        </html>
        """,
        "history": """
        <html>
            <head><title>History of {{ title }}</title></head>
            <body>
                <a href="/entries/{{ entry_id }}">← Back to Entry</a>
                <h1>Edit History: {{ title }}</h1>
                {% for edit in edits %}
                <div style="border-bottom: 1px solid #eee; margin-bottom: 10px;">
                    <p><strong>{{ edit.modified_at }}</strong> by {{ edit.modified_by }}</p>
                    <p><em>Summary: {{ edit.summary }}</em></p>
                    <pre style="background: #f4f4f4; padding: 5px;">{{ edit.content }}</pre>
                </div>
                {% endfor %}
            </body>
        </html>
        """
    }
    from jinja2 import Template
    tmpl = Template(templates_map[template_name])
    return HTMLResponse(content=tmpl.render(**context))

# --- API Endpoints ---

@app.get("/entries", response_class=HTMLResponse)
async def get_entries():
    with get_db() as conn:
        entries = conn.execute("SELECT id, title FROM entries").fetchall()
    return render_html("index", {"entries": entries})

@app.post("/entries", status_code=201)
async def create_entry(request: Request):
    # The OpenAPI says application/json, but for a webapp we usually use forms.
    # To support both, we check content type.
    try:
        # Try parsing as JSON first
        body = await request.json()
        new_entry = NewEntry(**body)
    except Exception:
        # Fallback to form data for the web UI
        form_data = await request.form()
        new_entry = NewEntry(
            title=form_data.get("title"),
            content=form_data.get("content"),
            createdBy=form_data.get("createdBy")
        )

    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    with get_db() as conn:
        conn.execute(
            "INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
            (entry_id, new_entry.title, new_entry.content, new_entry.createdBy, now)
        )
        conn.execute(
            "INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)",
            (entry_id, new_entry.content, new_entry.createdBy, "Initial creation", now)
        )
        conn.commit()
    
    return Entry(id=entry_id, title=new_entry.title, content=new_entry.content, 
                 lastModifiedBy=new_entry.createdBy, lastModifiedAt=now)

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        entry = {
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "lastModifiedBy": row["last_modified_by"],
            "lastModifiedAt": row["last_modified_at"]
        }
    return render_html("entry", {"entry": entry})

@app.put("/entries/{entryId}")
async def update_entry(entryId: str, request: Request):
    # Handle both JSON and Form
    try:
        body = await request.json()
        update_data = UpdateEntry(**body)
    except Exception:
        form_data = await request.form()
        update_data = UpdateEntry(
            content=form_data.get("content"),
            modifiedBy=form_data.get("modifiedBy"),
            summary=form_data.get("summary")
        )

    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        entry = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        conn.execute(
            "UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
            (update_data.content, update_data.modifiedBy, now, entryId)
        )
        conn.execute(
            "INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)",
            (entryId, update_data.content, update_data.modifiedBy, update_data.summary, now)
        )
        conn.commit()
        
        updated = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        return Entry(id=updated["id"], title=updated["title"], content=updated["content"], 
                     lastModifiedBy=updated["last_modified_by"], lastModifiedAt=updated["last_modified_at"])

# Overload POST for the web UI update form since HTML forms only support GET/POST
@app.post("/entries/{entryId}")
async def update_entry_post(entryId: str, request: Request):
    # This is a helper for the HTML form which cannot do PUT
    # We just call the logic of the PUT endpoint
    # We simulate a PUT request by calling the internal logic
    # Since we are in the same process, we can just reuse the logic
    # but to keep it clean, we'll just implement the update here.
    form_data = await request.form()
    update_data = UpdateEntry(
        content=form_data.get("content"),
        modifiedBy=form_data.get("modifiedBy"),
        summary=form_data.get("summary")
    )
    
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        entry = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        conn.execute(
            "UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
            (update_data.content, update_data.modifiedBy, now, entryId)
        )
        conn.execute(
            "INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)",
            (entryId, update_data.content, update_data.modifiedBy, update_data.summary, now)
        )
        conn.commit()
    
    # Redirect back to the entry page
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/entries/{entryId}", status_code=303)

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    with get_db() as conn:
        entry = conn.execute("SELECT title FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        edits = conn.execute(
            "SELECT content, modified_by, summary, modified_at FROM edits WHERE entry_id = ? ORDER BY modified_at DESC", 
            (entryId,)
        ).fetchall()
        
    return render_html("history", {
        "title": entry["title"],
        "entry_id": entryId,
        "edits": edits
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)