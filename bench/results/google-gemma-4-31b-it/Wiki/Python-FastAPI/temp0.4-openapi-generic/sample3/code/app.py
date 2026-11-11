import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Wiki API")
templates = Jinja2Templates(templating_dir=None) # We will use strings for templates to keep it in one file

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
                entryId TEXT NOT NULL,
                content TEXT NOT NULL,
                modifiedBy TEXT NOT NULL,
                summary TEXT,
                modifiedAt TEXT NOT NULL,
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
BASE_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        nav { margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #ccc; }
        .entry-box { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .meta { font-size: 0.8em; color: #666; }
        .diff-added { background-color: #e6ffed; color: #22863a; }
        .diff-removed { background-color: #ffeef0; color: #cb2431; }
        pre { background: #f4f4f4; padding: 10px; border-radius: 5px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <nav><a href="/entries">🏠 Home</a></nav>
    {{ content | safe }}
</body>
</html>
"""

INDEX_TEMPLATE = """
<h1>Wiki Entries</h1>
<div class="entry-box">
    <h3>Create New Entry</h3>
    <form action="/entries" method="post" enctype="application/json">
        <input type="hidden" name="__enctype" value="json">
        <input type="text" name="title" placeholder="Title" required><br>
        <textarea name="content" placeholder="Content" required></textarea><br>
        <input type="text" name="createdBy" placeholder="Your Name" required><br>
        <button type="submit">Create</button>
    </form>
    <p><i>Note: This form requires JSON body. Use the API docs or a tool for POST.</i></p>
</div>
<hr>
<ul>
    {% for entry in entries %}
    <li><a href="/entries/{{ entry.id }}">{{ entry.title }}</a></li>
    {% endfor %}
</ul>
"""

ENTRY_TEMPLATE = """
<h1>{{ entry.title }}</h1>
<div class="meta">
    Last modified by {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}
</div>
<div class="entry-box" style="margin-top: 20px;">
    <pre>{{ entry.content }}</pre>
</div>
<div style="margin-top: 20px;">
    <a href="/entries/{{ entry.id }}/edits">View History</a> | 
    <a href="/edit/{{ entry.id }}">Edit this page</a>
</div>
"""

HISTORY_TEMPLATE = """
<h1>History for {{ title }}</h1>
{% for edit in edits %}
<div class="entry-box" style="margin-bottom: 10px;">
    <div class="meta">Modified by <b>{{ edit.modifiedBy }}</b> on {{ edit.modifiedAt }}</div>
    <p><i>Summary: {{ edit.summary }}</i></p>
    <pre>{{ edit.content }}</pre>
</div>
{% endfor %}
"""

# --- Routes ---

@app.get("/entries", response_class=HTMLResponse)
async def get_entries():
    with get_db() as conn:
        rows = conn.execute("SELECT id, title FROM entries").fetchall()
        entries = [{"id": r["id"], "title": r["title"]} for r in rows]
    
    content = templates.Template(INDEX_TEMPLATE).render(entries=entries)
    return templates.Template(BASE_LAYOUT).render(content=content)

@app.post("/entries", status_code=201, response_model=Entry)
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
    return Entry(id=entry_id, title=entry.title, content=entry.content, lastModifiedBy=entry.createdBy, lastModifiedAt=now)

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        entry = dict(row)
    
    content = templates.Template(ENTRY_TEMPLATE).render(entry=entry)
    return templates.Template(BASE_LAYOUT).render(content=content)

@app.put("/entries/{entryId}", response_model=Entry)
async def update_entry(entryId: str, update: UpdateEntry):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
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
        return Entry(**dict(updated_row))

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    with get_db() as conn:
        entry = conn.execute("SELECT title FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        rows = conn.execute("SELECT content, modifiedBy, summary, modifiedAt FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", (entryId,)).fetchall()
        edits = [dict(r) for r in rows]
    
    content = templates.Template(HISTORY_TEMPLATE).render(title=entry["title"], edits=edits)
    return templates.Template(BASE_LAYOUT).render(content=content)

# Helper route for a simple edit form (not in OpenAPI but useful for the webapp)
@app.get("/edit/{entryId}", response_class=HTMLResponse)
async def edit_page(entryId: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row: raise HTTPException(status_code=404)
        entry = dict(row)
    
    edit_form = f"""
    <h1>Editing {entry['title']}</h1>
    <form action="/update-entry-form" method="post">
        <input type="hidden" name="entryId" value="{entry['id']}">
        <textarea name="content" style="width:100%; height:300px;">{entry['content']}</textarea><br>
        <input type="text" name="modifiedBy" placeholder="Your Name" required><br>
        <input type="text" name="summary" placeholder="What did you change?" required><br>
        <button type="submit">Save Changes</button>
    </form>
    """
    return templates.Template(BASE_LAYOUT).render(content=edit_form)

@app.post("/update-entry-form")
async def handle_update_form(entryId: str = Form(...), content: str = Form(...), modifiedBy: str = Form(...), summary: str = Form(...)):
    update_data = UpdateEntry(content=content, modifiedBy=modifiedBy, summary=summary)
    await update_entry(entryId, update_data)
    return templates.Template(BASE_LAYOUT).render(content=f'<p>Updated successfully! <a href="/entries/{entryId}">Go back</a></p>')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)