import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template, escape

app = FastAPI(title="Wiki API")

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
    title: str = Field(..., max_length=1000)
    content: str = Field(..., max_length=100000)
    createdBy: str = Field(..., max_length=255)

class UpdateEntry(BaseModel):
    content: str = Field(..., max_length=100000)
    modifiedBy: str = Field(..., max_length=255)
    summary: str = Field(..., max_length=500)

# --- HTML Templates (Inline) ---
# We use Jinja2's Template. By default, Jinja2 does not escape variables 
# unless we use the environment's autoescape or call escape() explicitly.
# To prevent XSS, we wrap the rendering in a way that ensures content is escaped.

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Wiki Home</title></head>
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
<html lang="en">
<head><meta charset="UTF-8"><title>{{ entry.title }}</title></head>
<body>
    <a href="/entries">« Back to Home</a>
    <h1>{{ entry.title }}</h1>
    <div style="border: 1px solid #ccc; padding: 10px; background: #f9f9f9; white-space: pre-wrap;">
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
<html lang="en">
<head><meta charset="UTF-8"><title>History - {{ title }}</title></head>
<body>
    <a href="/entries">« Back to Home</a> | <a href="/entries/{{ entry_id }}">« Back to Entry</a>
    <h1>Edit History for {{ title }}</h1>
    {% for edit in edits %}
    <div style="border-bottom: 1px solid #ddd; margin-bottom: 10px;">
        <p><strong>User:</strong> {{ edit.modifiedBy }} | <strong>Date:</strong> {{ edit.modifiedAt }}</p>
        <p><strong>Summary:</strong> {{ edit.summary }}</p>
        <pre style="background: #eee; padding: 5px; white-space: pre-wrap;">{{ edit.content }}</pre>
    </div>
    {% endfor %}
</body>
</html>
"""

def render_html(template_str: str, context: dict):
    # Use Jinja2 Template with explicit escaping for all context values to prevent XSS
    # We create a new template and manually escape values in the context
    escaped_context = {}
    for k, v in context.items():
        if isinstance(v, list):
            escaped_context[k] = [
                {ik: escape(iv) if isinstance(iv, str) else iv for ik, iv in item.items()} 
                if isinstance(item, dict) else escape(item) 
                for item in v
            ]
        elif isinstance(v, dict):
            escaped_context[k] = {ik: escape(iv) if isinstance(iv, str) else iv for ik, iv in v.items()}
        else:
            escaped_context[k] = escape(v) if isinstance(v, str) else v
            
    return Template(template_str).render(**escaped_context)

# --- Routes ---

@app.get("/entries", response_class=HTMLResponse)
async def get_entries():
    try:
        with get_db() as conn:
            rows = conn.execute("SELECT id, title FROM entries").fetchall()
            entries = [{"id": row["id"], "title": row["title"]} for row in rows]
        return render_html(INDEX_TEMPLATE, {"entries": entries})
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/entries", status_code=201)
async def create_entry(entry: NewEntry):
    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    try:
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
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/entries", response_class=HTMLResponse)
async def create_entry_html(request: Request):
    try:
        form_data = await request.form()
        # Validate input lengths manually for form data to match Pydantic constraints
        title = form_data.get("title", "")
        content = form_data.get("content", "")
        createdBy = form_data.get("createdBy", "")
        
        if not title or not content or not createdBy:
             raise HTTPException(status_code=400, detail="Missing required fields")
        
        if len(title) > 1000 or len(content) > 100000 or len(createdBy) > 255:
             raise HTTPException(status_code=400, detail="Input too long")

        new_entry = NewEntry(title=title, content=content, createdBy=createdBy)
        await create_entry(new_entry)
        # The spec says /entries GET returns the list. After POST, we return the list page.
        with get_db() as conn:
            rows = conn.execute("SELECT id, title FROM entries").fetchall()
            entries = [{"id": row["id"], "title": row["title"]} for row in rows]
        return render_html(INDEX_TEMPLATE, {"entries": entries})
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    # entryId is a UUID string, we should ensure it doesn't contain malicious patterns, 
    # though parameterized queries handle SQLi.
    try:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Entry not found")
            entry = dict(row)
        return render_html(ENTRY_TEMPLATE, {"entry": entry})
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.put("/entries/{entryId}")
async def update_entry(entryId: str, update: UpdateEntry):
    now = datetime.utcnow().isoformat()
    try:
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
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/entries/{entryId}", response_class=HTMLResponse)
async def update_entry_html(entryId: str, request: Request):
    try:
        form_data = await request.form()
        content = form_data.get("content", "")
        modifiedBy = form_data.get("modifiedBy", "")
        summary = form_data.get("summary", "")
        
        if not content or not modifiedBy or not summary:
             raise HTTPException(status_code=400, detail="Missing required fields")
        
        if len(content) > 100000 or len(modifiedBy) > 255 or len(summary) > 500:
             raise HTTPException(status_code=400, detail="Input too long")

        update_data = UpdateEntry(content=content, modifiedBy=modifiedBy, summary=summary)
        await update_entry(entryId, update_data)
        
        with get_db() as conn:
            row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
            return render_html(ENTRY_TEMPLATE, {"entry": dict(row)})
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    try:
        with get_db() as conn:
            entry = conn.execute("SELECT title FROM entries WHERE id = ?", (entryId,)).fetchone()
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")
            
            rows = conn.execute("SELECT content, modifiedBy, summary, modifiedAt FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", (entryId,)).fetchall()
            edits = [dict(row) for row in rows]
        
        return render_html(HISTORY_TEMPLATE, {"title": entry["title"], "entry_id": entryId, "edits": edits})
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)