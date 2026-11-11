import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template, escape

app = FastAPI(title="Wiki API")

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
    title: str = Field(..., max_length=1000)
    content: str = Field(..., max_length=100000)
    createdBy: str = Field(..., max_length=255)

class UpdateEntry(BaseModel):
    content: str = Field(..., max_length=100000)
    modifiedBy: str = Field(..., max_length=255)
    summary: str = Field(..., max_length=500)

# HTML Templates as strings. 
# Note: Jinja2 auto-escapes variables when using render(), 
# but we use explicit escape() for safety in custom logic if needed.
BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Wiki</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-box { border: 1px solid #ddd; padding: 20px; border-radius: 8px; white-space: pre-wrap; }
        .meta { font-size: 0.8em; color: #666; margin-bottom: 20px; }
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
        <textarea name="content" required>{{ content }}</textarea>
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
        <strong style="display:block">{{ edit.modifiedBy }}</strong> 
        <small>{{ edit.modifiedAt }}</small><br>
        <em>"{{ edit.summary }}"</em>
        <pre style="border: 1px solid #eee; padding: 5px; margin-top: 10px;">{{ edit.content }}</pre>
    </div>
    {% endfor %}
""")

def render_html(template_str, **kwargs):
    # Jinja2 Template automatically escapes variables passed into it
    return Template(template_str).render(**kwargs)

# API Endpoints

@app.get("/entries", response_class=HTMLResponse)
async def get_entries():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM entries")
            entries = [{"id": row[0], "title": row[1]} for row in cursor.fetchall()]
        return render_html(INDEX_TEMPLATE, entries=entries)
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/entries", status_code=201)
async def create_entry(entry: NewEntry):
    try:
        entry_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Parameterized query prevents SQL Injection
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
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    # entryId is a string from path, parameterized query handles it safely
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, content, lastModifiedBy, lastModifiedAt FROM entries WHERE id = ?", (entryId,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Entry not found")
            entry = {"id": row[0], "title": row[1], "content": row[2], "lastModifiedBy": row[3], "lastModifiedAt": row[4]}
        return render_html(ENTRY_TEMPLATE, entry=entry)
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.put("/entries/{entryId}")
async def update_entry(entryId: str, update: UpdateEntry):
    try:
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
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    try:
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
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

# UI Helper Routes

@app.get("/create", response_class=HTMLResponse)
async def create_page():
    return render_html(CREATE_TEMPLATE)

@app.post("/create", response_class=HTMLResponse)
async def create_post(request: Request):
    try:
        form_data = await request.form()
        # Validate lengths to prevent resource exhaustion
        title = form_data.get("title", "")[:1000]
        content = form_data.get("content", "")[:100000]
        createdBy = form_data.get("createdBy", "")[:255]
        
        if not title or not content or not createdBy:
            return render_html(CREATE_TEMPLATE) # Simple validation failure

        new_entry = NewEntry(title=title, content=content, createdBy=createdBy)
        await create_entry(new_entry)
        # Return index
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM entries")
            entries = [{"id": row[0], "title": row[1]} for row in cursor.fetchall()]
        return render_html(INDEX_TEMPLATE, entries=entries)
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/entries/{entryId}/edit", response_class=HTMLResponse)
async def edit_page(entryId: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT title, content FROM entries WHERE id = ?", (entryId,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Entry not found")
        return render_html(EDIT_TEMPLATE, title=row[0], content=row[1])
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/entries/{entryId}/edit", response_class=HTMLResponse)
async def edit_post(entryId: str, request: Request):
    try:
        form_data = await request.form()
        content = form_data.get("content", "")[:100000]
        modifiedBy = form_data.get("modifiedBy", "")[:255]
        summary = form_data.get("summary", "")[:500]
        
        if not content or not modifiedBy or not summary:
            return render_html(EDIT_TEMPLATE, title="Error", content="")

        update = UpdateEntry(content=content, modifiedBy=modifiedBy, summary=summary)
        await update_entry(entryId, update)
        
        # Return the entry page
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, content, lastModifiedBy, lastModifiedAt FROM entries WHERE id = ?", (entryId,))
            row = cursor.fetchone()
            entry = {"id": row[0], "title": row[1], "content": row[2], "lastModifiedBy": row[3], "lastModifiedAt": row[4]}
        return render_html(ENTRY_TEMPLATE, entry=entry)
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)