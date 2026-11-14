import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Form
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

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                last_modified_by TEXT NOT NULL,
                last_modified_at TEXT NOT NULL
            )
        """)
        # Edits history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                content TEXT NOT NULL,
                modified_by TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                summary TEXT NOT NULL,
                FOREIGN KEY(entry_id) REFERENCES entries(id)
            )
        """)
        conn.commit()

init_db()

# --- App Setup ---
app = FastAPI(title="Wiki API")
templates = Jinja2Templates(request=Request)

# Since we are restricted to one file and cannot create external HTML files, 
# we define HTML templates as strings and use Jinja2's Template class directly 
# or use a helper to render. However, Jinja2Templates usually expects a directory.
# We will use a custom render function with Jinja2.Template for simplicity in a single file.
from jinja2 import Template

LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-box { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .diff { background: #f9f9f9; padding: 10px; border-left: 3px solid #ccc; white-space: pre-wrap; }
        .meta { color: #666; font-size: 0.9em; }
        form div { margin-bottom: 10px; }
        label { display: block; font-weight: bold; }
        input[type="text"], textarea { width: 100%; padding: 8px; box-sizing: border-box; }
    </style>
</head>
<body>
    <nav><a href="/entries">🏠 Home</a></nav>
    {{ content }}
</body>
</html>
"""

def render_page(content_html):
    return HTMLResponse(Template(LAYOUT).render(content=content_html))

# --- Routes ---

@app.get("/entries", response_class=HTMLResponse)
async def get_entries():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title FROM entries")
        rows = cursor.fetchall()
    
    html = "<h1>Wiki Entries</h1>"
    html += "<ul>"
    for row in rows:
        html += f"<li><a href='/entries/{row[0]}'>{row[1]}</a></li>"
    html += "</ul>"
    html += '<hr><h3>Create New Entry</h3>'
    html += '''
    <form action="/entries" method="post">
        <div><label>Title</label><input type="text" name="title" required></div>
        <div><label>Content</label><textarea name="content" required></textarea></div>
        <div><label>Your Name</label><input type="text" name="createdBy" required></div>
        <button type="submit">Create</button>
    </form>
    '''
    return render_page(html)

@app.post("/entries", status_code=201)
async def create_entry(request: Request):
    # The OpenAPI says application/json, but for a webapp we handle form data
    # To satisfy both, we check content type or just use form for the UI
    form_data = await request.form()
    title = form_data.get("title")
    content = form_data.get("content")
    created_by = form_data.get("createdBy")
    
    if not title or not content or not created_by:
        raise HTTPException(status_code=400, detail="Missing fields")

    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
                       (entry_id, title, content, created_by, now))
        # Initial edit record
        cursor.execute("INSERT INTO edits (entry_id, content, modified_by, modified_at, summary) VALUES (?, ?, ?, ?, ?)",
                       (entry_id, content, created_by, now, "Initial creation"))
        conn.commit()
    
    return {"id": entry_id, "title": title, "content": content, "lastModifiedBy": created_by, "lastModifiedAt": now}

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", (entryId,))
        row = cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    eid, title, content, user, date = row
    
    html = f"<h1>{title}</h1>"
    html += f"<p class='meta'>Last edited by {user} on {date}</p>"
    html += f"<div class='entry-box'>{content}</div>"
    html += f"<p><a href='/entries/{eid}/edits'>View History</a></p>"
    html += '<hr><h3>Edit this page</h3>'
    html += f'''
    <form action="/entries/{eid}" method="post">
        <div><label>Content</label><textarea name="content" required>{content}</textarea></div>
        <div><label>Your Name</label><input type="text" name="modifiedBy" required></div>
        <div><label>Edit Summary</label><input type="text" name="summary" required></div>
        <button type="submit">Save Changes</button>
    </form>
    '''
    return render_page(html)

@app.post("/entries/{entryId}") # Using POST for the form update to simplify
@app.put("/entries/{entryId}")
async def update_entry(entryId: str, request: Request):
    # Handle both JSON (API) and Form (Web)
    content_type = request.headers.get('content-type', '')
    if 'application/json' in content_type:
        data = await request.json()
    else:
        form_data = await request.form()
        data = {k: v for k, v in form_data.items()}

    content = data.get("content")
    modified_by = data.get("modifiedBy")
    summary = data.get("summary")

    if not content or not modified_by or not summary:
        raise HTTPException(status_code=400, detail="Missing fields")

    now = datetime.utcnow().isoformat()
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM entries WHERE id = ?", (entryId,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Entry not found")
        
        cursor.execute("UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
                       (content, modified_by, now, entryId))
        cursor.execute("INSERT INTO edits (entry_id, content, modified_by, modified_at, summary) VALUES (?, ?, ?, ?, ?)",
                       (entryId, content, modified_by, now, summary))
        conn.commit()
    
    # Fetch updated entry for response
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", (entryId,))
    row = cursor.fetchone()
    return {"id": row[0], "title": row[1], "content": row[2], "lastModifiedBy": row[3], "lastModifiedAt": row[4]}

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM entries WHERE id = ?", (entryId,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Entry not found")
        
        cursor.execute("SELECT content, modified_by, modified_at, summary FROM edits WHERE entry_id = ? ORDER BY modified_at DESC", (entryId,))
        edits = cursor.fetchall()

    html = f"<h1>Edit History for {entryId}</h1>"
    html += "<ul>"
    for edit in edits:
        content, user, date, summary = edit
        html += f"<li>"
        html += f"<strong>{user}</strong> at {date} - <em>{summary}</em>"
        html += f"<div class='diff'>{content}</div>"
        html += "</li><br>"
    html += "</ul>"
    return render_page(html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)