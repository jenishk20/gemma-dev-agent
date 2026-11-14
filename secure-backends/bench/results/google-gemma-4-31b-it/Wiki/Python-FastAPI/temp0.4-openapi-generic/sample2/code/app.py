import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

app = FastAPI(title="Wiki API")
templates = Jinja2Templates(directory=".") # We will use inline templates via Jinja2's Template class if needed, but here we use a trick to avoid external files by defining strings.

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
                lastModifiedBy TEXT,
                lastModifiedAt TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entryId TEXT,
                content TEXT,
                modifiedBy TEXT,
                summary TEXT,
                timestamp TEXT,
                FOREIGN KEY(entryId) REFERENCES entries(id)
            )
        """)
        conn.commit()

init_db()

# --- Schemas ---
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

# --- HTML Templates (Inline) ---
# Since we cannot create separate files, we define HTML as strings and use Jinja2 to render them.
# We use a simple helper to render these strings.
from jinja2 import Template

BASE_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        .container { max-width: 800px; margin: auto; }
        .entry-link { display: block; margin: 10px 0; font-size: 1.2em; }
        .meta { color: #666; font-size: 0.9em; }
        .diff-added { background-color: #dfd; }
        .diff-removed { background-color: #fdd; text-decoration: line-through; }
        .nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        textarea { width: 100%; height: 300px; }
        .edit-card { border: 1px solid #ccc; padding: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/entries">🏠 Home</a> | <a href="/entries/new">➕ New Page</a>
        </div>
        {{ content }}
    </div>
</body>
</html>
"""

INDEX_TEMPLATE = """
<h1>Wiki Entries</h1>
{% for entry in entries %}
    <a class="entry-link" href="/entries/{{ entry.id }}">{{ entry.title }}</a>
{% endfor %}
{% if not entries %}
    <p>No entries yet. Create the first one!</p>
{% endif %}
"""

ENTRY_TEMPLATE = """
<h1>{{ entry.title }}</h1>
<div class="meta">
    Last modified by {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}
</div>
<hr>
<div>{{ entry.content }}</div>
<hr>
<div class="nav">
    <a href="/entries/{{ entry.id }}/edit">📝 Edit this page</a> | 
    <a href="/entries/{{ entry.id }}/edits">📜 History</a>
</div>
"""

EDIT_TEMPLATE = """
<h1>Edit Page: {{ title }}</h1>
<form method="post" action="/entries/{{ entry_id }}/update">
    <label>Content:</label><br>
    <textarea name="content">{{ content }}</textarea><br>
    <label>Your Name:</label><br>
    <input type="text" name="modifiedBy" required><br>
    <label>Edit Summary:</label><br>
    <input type="text" name="summary" required><br><br>
    <button type="submit">Save Changes</button>
</form>
"""

HISTORY_TEMPLATE = """
<h1>Edit History for {{ title }}</h1>
{% for edit in edits %}
    <div class="edit-card">
        <strong>{{ edit.modifiedBy }}</strong> - {{ edit.timestamp }}<br>
        <em>Summary: {{ edit.summary }}</em><br>
        <pre>{{ edit.content }}</pre>
    </div>
{% endfor %}
"""

NEW_PAGE_TEMPLATE = """
<h1>Create New Entry</h1>
<form method="post" action="/entries/create">
    <label>Title:</label><br>
    <input type="text" name="title" required><br>
    <label>Content:</label><br>
    <textarea name="content" required></textarea><br>
    <label>Your Name:</label><br>
    <input type="text" name="createdBy" required><br><br>
    <button type="submit">Create Page</button>
</form>
"""

def render_page(template_str, **kwargs):
    content = Template(template_str).render(**kwargs)
    return HTMLResponse(content=Template(BASE_LAYOUT).render(content=content))

# --- Routes ---

@app.get("/entries", response_class=HTMLResponse)
async def get_entries():
    with get_db() as conn:
        rows = conn.execute("SELECT id, title FROM entries").fetchall()
        entries = [dict(row) for row in rows]
    return render_page(INDEX_TEMPLATE, entries=entries)

@app.post("/entries/create", response_class=HTMLResponse)
async def create_entry_html(request: Request):
    form_data = await request.form()
    title = form_data.get("title")
    content = form_data.get("content")
    createdBy = form_data.get("createdBy")
    
    if not all([title, content, createdBy]):
        raise HTTPException(status_code=400, detail="Missing fields")
    
    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    with get_db() as conn:
        conn.execute("INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)",
                     (entry_id, title, content, createdBy, now))
        conn.execute("INSERT INTO edits (entryId, content, modifiedBy, summary, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (entry_id, content, createdBy, "Initial creation", now))
        conn.commit()
    
    return render_page(INDEX_TEMPLATE, entries=[{"id": entry_id, "title": title}]) # Simplified redirect

@app.post("/entries", status_code=201)
async def create_entry_api(entry: NewEntry):
    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute("INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)",
                     (entry_id, entry.title, entry.content, entry.createdBy, now))
        conn.execute("INSERT INTO edits (entryId, content, modifiedBy, summary, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (entry_id, entry.content, entry.createdBy, "Initial creation", now))
        conn.commit()
    return Entry(id=entry_id, title=entry.title, content=entry.content, lastModifiedBy=entry.createdBy, lastModifiedAt=now)

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        entry = dict(row)
    return render_page(ENTRY_TEMPLATE, entry=entry)

@app.get("/entries/{entryId}/edit", response_class=HTMLResponse)
async def edit_entry_page(entryId: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        entry = dict(row)
    return render_page(EDIT_TEMPLATE, entry_id=entryId, title=entry['title'], content=entry['content'])

@app.post("/entries/{entryId}/update", response_class=HTMLResponse)
async def update_entry_html(entryId: str, request: Request):
    form_data = await request.form()
    content = form_data.get("content")
    modifiedBy = form_data.get("modifiedBy")
    summary = form_data.get("summary")
    
    if not all([content, modifiedBy, summary]):
        raise HTTPException(status_code=400, detail="Missing fields")
    
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT id FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        conn.execute("UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?",
                     (content, modifiedBy, now, entryId))
        conn.execute("INSERT INTO edits (entryId, content, modifiedBy, summary, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (entryId, content, modifiedBy, summary, now))
        conn.commit()
        
    return render_page(INDEX_TEMPLATE, entries=[]) # Redirect to home or entry

@app.put("/entries/{entryId}")
async def update_entry_api(entryId: str, update: UpdateEntry):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        conn.execute("UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?",
                     (update.content, update.modifiedBy, now, entryId))
        conn.execute("INSERT INTO edits (entryId, content, modifiedBy, summary, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (entryId, update.content, update.modifiedBy, update.summary, now))
        conn.commit()
        
        updated_row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        return Entry(**dict(updated_row))

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        title = conn.execute("SELECT title FROM entries WHERE id = ?", (entryId,)).fetchone()['title']
        edits_rows = conn.execute("SELECT * FROM edits WHERE entryId = ? ORDER BY timestamp DESC", (entryId,)).fetchall()
        edits = [dict(r) for r in edits_rows]
        
    return render_page(HISTORY_TEMPLATE, title=title, edits=edits)

@app.get("/entries/new", response_class=HTMLResponse)
async def new_page_ui():
    return render_page(NEW_PAGE_TEMPLATE)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)