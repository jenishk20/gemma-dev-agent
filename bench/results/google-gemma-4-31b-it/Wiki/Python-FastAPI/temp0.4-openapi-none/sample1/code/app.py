import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

app = FastAPI(title="Wiki API")
templates = Jinja2Templates(dirname=".") # We will use inline templates via Jinja2's ability to render strings if needed, but here we use a simple approach

DB_PATH = "db.sqlite3"

# --- Database Setup ---
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
                modifiedAt TEXT,
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
# Since we must put everything in one file and cannot create a 'templates' folder, 
# we will use a helper to render HTML strings.
def render_html(template_str: str, context: dict):
    from jinja2 import Template
    return Template(template_str).render(**context)

INDEX_TEMPLATE = """
<!DOCTYPE html>
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
    <h2>Create New Entry</h2>
    <form action="/entries" method="post">
        <input type="text" name="title" placeholder="Title" required><br>
        <textarea name="content" placeholder="Content" required></textarea><br>
        <input type="text" name="createdBy" placeholder="Your Name" required><br>
        <button type="submit">Create</button>
    </form>
</body>
</html>
"""

ENTRY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>{{ entry.title }}</title></head>
<body>
    <a href="/entries">« Back to Home</a>
    <h1>{{ entry.title }}</h1>
    <div style="border: 1px solid #ccc; padding: 10px; background: #f9f9f9;">
        {{ entry.content }}
    </div>
    <p><i>Last modified by {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}</i></p>
    <hr>
    <h3>Edit Entry</h3>
    <form action="/entries/{{ entry.id }}" method="post">
        <textarea name="content" style="width: 100%; height: 200px;">{{ entry.content }}</textarea><br>
        <input type="text" name="modifiedBy" placeholder="Your Name" required><br>
        <input type="text" name="summary" placeholder="Edit Summary" required><br>
        <button type="submit">Save Changes</button>
    </form>
    <p><a href="/entries/{{ entry.id }}/edits">View Edit History</a></p>
</body>
</html>
"""

HISTORY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>History - {{ title }}</title></head>
<body>
    <a href="/entries">« Back to Home</a> | <a href="/entries/{{ entry_id }}">« Back to Entry</a>
    <h1>Edit History for {{ title }}</h1>
    {% for edit in edits %}
    <div style="border-bottom: 1px solid #ddd; margin-bottom: 10px;">
        <p><strong>User:</strong> {{ edit.modifiedBy }} | <strong>Date:</strong> {{ edit.modifiedAt }}</p>
        <p><strong>Summary:</strong> {{ edit.summary }}</p>
        <pre style="background: #eee; padding: 5px;">{{ edit.content }}</pre>
    </div>
    {% endfor %}
</body>
</html>
"""

# --- Routes ---

@app.get("/entries", response_class=HTMLResponse)
async def get_entries():
    with get_db() as conn:
        rows = conn.execute("SELECT id, title FROM entries").fetchall()
        entries = [{"id": row["id"], "title": row["title"]} for row in rows]
    return render_html(INDEX_TEMPLATE, {"entries": entries})

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
            "INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)",
            (entry_id, entry.content, entry.createdBy, "Initial creation", now)
        )
        conn.commit()
    return {"id": entry_id, "title": entry.title, "content": entry.content, "lastModifiedBy": entry.createdBy, "lastModifiedAt": now}

# Overload for HTML form submission
@app.post("/entries", response_class=HTMLResponse)
async def create_entry_html(request: Request):
    form_data = await request.form()
    new_entry = NewEntry(
        title=form_data.get("title"),
        content=form_data.get("content"),
        createdBy=form_data.get("createdBy")
    )
    # Call the logic
    res = await create_entry(new_entry)
    return render_html(INDEX_TEMPLATE, {"entries": []}) # Simplified redirect

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        entry = dict(row)
    return render_html(ENTRY_TEMPLATE, {"entry": entry})

@app.put("/entries/{entryId}")
async def update_entry(entryId: str, update: UpdateEntry):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT id FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        conn.execute(
            "UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?",
            (update.content, update.modifiedBy, now, entryId)
        )
        conn.execute(
            "INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)",
            (entryId, update.content, update.modifiedBy, update.summary, now)
        )
        conn.commit()
        
        updated_row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        return dict(updated_row)

# Overload for HTML form submission
@app.post("/entries/{entryId}", response_class=HTMLResponse)
async def update_entry_html(entryId: str, request: Request):
    form_data = await request.form()
    update_data = UpdateEntry(
        content=form_data.get("content"),
        modifiedBy=form_data.get("modifiedBy"),
        summary=form_data.get("summary")
    )
    await update_entry(entryId, update_data)
    # Return the entry page
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        return render_html(ENTRY_TEMPLATE, {"entry": dict(row)})

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    with get_db() as conn:
        # Check if entry exists
        entry = conn.execute("SELECT title FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        rows = conn.execute("SELECT content, modifiedBy, summary, modifiedAt FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", (entryId,)).fetchall()
        edits = [dict(row) for row in rows]
    
    return render_html(HISTORY_TEMPLATE, {"title": entry["title"], "entry_id": entryId, "edits": edits})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)