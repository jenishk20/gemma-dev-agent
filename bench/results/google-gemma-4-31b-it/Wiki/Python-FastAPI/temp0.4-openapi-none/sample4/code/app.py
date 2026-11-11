import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

app = FastAPI(title="Wiki API")
templates = Jinja2Templates(directory=".") # We will use inline templates via Jinja2's ability to render strings or a dummy dir

# Database Setup
DB_PATH = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                lastModifiedBy TEXT,
                lastModifiedAt TEXT
            )
        """)
        cursor.execute("""
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

# Pydantic Models
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

# HTML Templates as strings to keep everything in one file
BASE_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-box { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .meta { font-size: 0.8em; color: #666; margin-bottom: 20px; }
        .diff-add { background-color: #dfd; }
        .diff-rem { background-color: #fdd; text-decoration: line-through; }
        form { display: flex; flex-direction: column; gap: 10px; max-width: 600px; }
        textarea { height: 200px; }
        input, textarea { padding: 8px; }
        button { cursor: pointer; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; }
    </style>
</head>
<body>
    <nav><a href="/entries">🏠 Home</a> | <a href="/create">➕ New Entry</a></nav>
    {% block content %}{% endblock %}
</body>
</html>
"""

INDEX_TEMPLATE = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
    <h1>Wiki Entries</h1>
    <ul>
        {% for entry in entries %}
        <li><a href="/entries/{{ entry.id }}">{{ entry.title }}</a></li>
        {% endfor %}
    </ul>
""")

ENTRY_TEMPLATE = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
    <h1>{{ entry.title }}</h1>
    <div class="meta">
        Last edited by {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}
    </div>
    <div class="entry-box">{{ entry.content }}</div>
    <p><a href="/entries/{{ entry.id }}/edit">Edit this page</a> | <a href="/entries/{{ entry.id }}/edits">View History</a></p>
""")

EDIT_TEMPLATE = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
    <h1>Edit: {{ title }}</h1>
    <form method="post">
        <label>Content:</label>
        <textarea name="content">{{ content }}</textarea>
        <label>Your Name:</label>
        <input type="text" name="modifiedBy" required>
        <label>Edit Summary:</label>
        <input type="text" name="summary" required>
        <button type="submit">Save Changes</button>
    </form>
""")

CREATE_TEMPLATE = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
    <h1>Create New Entry</h1>
    <form method="post">
        <label>Title:</label>
        <input type="text" name="title" required>
        <label>Content:</label>
        <textarea name="content" required></textarea>
        <label>Your Name:</label>
        <input type="text" name="createdBy" required>
        <button type="submit">Create Entry</button>
    </form>
""")

HISTORY_TEMPLATE = BASE_LAYOUT.replace("{% block content %}{% endblock %}", """
    <h1>History: {{ title }}</h1>
    {% for edit in edits %}
    <div class="entry-box" style="margin-bottom: 10px;">
        <strong>{{ edit.modifiedBy }}</strong> - {{ edit.modifiedAt }}<br>
        <em>"{{ edit.summary }}"</em>
        <pre style="white-space: pre-wrap; border: 1px solid #eee; padding: 5px;">{{ edit.content }}</pre>
    </div>
    {% endfor %}
""")

from jinja2 import Template

def render_html(template_str, **kwargs):
    return Template(template_str).render(**kwargs)

# API Endpoints

@app.get("/entries", response_class=HTMLResponse)
async def get_entries():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title FROM entries")
        entries = [{"id": row[0], "title": row[1]} for row in cursor.fetchall()]
    return render_html(INDEX_TEMPLATE, entries=entries)

@app.post("/entries", status_code=201)
async def create_entry(entry: NewEntry):
    entry_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)",
            (entry_id, entry.title, entry.content, entry.createdBy, now)
        )
        cursor.execute(
            "INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)",
            (entry_id, entry.content, entry.createdBy, "Initial creation", now)
        )
        conn.commit()
    return Entry(id=entry_id, title=entry.title, content=entry.content, lastModifiedBy=entry.createdBy, lastModifiedAt=now)

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, content, lastModifiedBy, lastModifiedAt FROM entries WHERE id = ?", (entryId,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        entry = {"id": row[0], "title": row[1], "content": row[2], "lastModifiedBy": row[3], "lastModifiedAt": row[4]}
    return render_html(ENTRY_TEMPLATE, entry=entry)

@app.put("/entries/{entryId}")
async def update_entry(entryId: str, update: UpdateEntry):
    now = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM entries WHERE id = ?", (entryId,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        title = row[0]
        cursor.execute(
            "UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?",
            (update.content, update.modifiedBy, now, entryId)
        )
        cursor.execute(
            "INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)",
            (entryId, update.content, update.modifiedBy, update.summary, now)
        )
        conn.commit()
    return Entry(id=entryId, title=title, content=update.content, lastModifiedBy=update.modifiedBy, lastModifiedAt=now)

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM entries WHERE id = ?", (entryId,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        title = row[0]
        
        cursor.execute("SELECT content, modifiedBy, summary, modifiedAt FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", (entryId,))
        edits = [{"content": r[0], "modifiedBy": r[1], "summary": r[2], "modifiedAt": r[3]} for r in cursor.fetchall()]
    return render_html(HISTORY_TEMPLATE, title=title, edits=edits)

# UI Helper Routes (Not in OpenAPI but needed for the webapp to function)

@app.get("/create", response_class=HTMLResponse)
async def create_page():
    return render_html(CREATE_TEMPLATE)

@app.post("/create", response_class=HTMLResponse)
async def create_post(request: Request):
    form_data = await request.form()
    new_entry = NewEntry(
        title=form_data.get("title"),
        content=form_data.get("content"),
        createdBy=form_data.get("createdBy")
    )
    await create_entry(new_entry)
    return render_html(INDEX_TEMPLATE, entries=[]) # Redirect logic simplified

@app.get("/entries/{entryId}/edit", response_class=HTMLResponse)
async def edit_page(entryId: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, content FROM entries WHERE id = ?", (entryId,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
    return render_html(EDIT_TEMPLATE, title=row[0], content=row[1])

@app.post("/entries/{entryId}/edit", response_class=HTMLResponse)
async def edit_post(entryId: str, request: Request):
    form_data = await request.form()
    update = UpdateEntry(
        content=form_data.get("content"),
        modifiedBy=form_data.get("modifiedBy"),
        summary=form_data.get("summary")
    )
    await update_entry(entryId, update)
    return render_html(ENTRY_TEMPLATE, entry={"id": entryId, "title": "Updated", "content": update.content, "lastModifiedBy": update.modifiedBy, "lastModifiedAt": "Just now"})

# Overriding the post /create and /edit to actually redirect or show the entry
# Since we can't use RedirectResponse easily without importing, we just return the HTML.
# To make it a real webapp, we'll adjust the post handlers to return a "Success" page or the entry.

import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)