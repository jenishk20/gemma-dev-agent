import sqlite3
import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import uvicorn

# --- Models ---
class Entry(BaseModel):
    id: str
    title: str
    content: str
    lastModifiedBy: str
    lastModifiedAt: datetime.datetime

class NewEntry(BaseModel):
    title: str
    content: str
    createdBy: str

class UpdateEntry(BaseModel):
    content: str
    modifiedBy: str
    summary: str

# --- Database Logic ---
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
                last_modified_by TEXT NOT NULL,
                last_modified_at TIMESTAMP NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                content TEXT NOT NULL,
                modified_by TEXT NOT NULL,
                summary TEXT NOT NULL,
                modified_at TIMESTAMP NOT NULL,
                FOREIGN KEY(entry_id) REFERENCES entries(id)
            )
        """)
        conn.commit()

# --- App Setup ---
app = FastAPI(title="Wiki API")
templates = Jinja2Templates(dirname=".") # We use inline templates via strings since we can't create files

# Since we can't create a 'templates' folder, we define a simple helper to render HTML
# using Jinja2 directly from strings.
from jinja2 import Template

def render_wiki_html(template_str: str, **kwargs):
    template = Template(template_str)
    return template.render(**kwargs)

HTML_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki - {{ title }}</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f4; }
        .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        a { color: #0066cc; }
        .meta { font-size: 0.8em; color: #666; margin-bottom: 20px; }
        .edit-item { border-bottom: 1px solid #eee; padding: 10px 0; }
        .diff-old { color: red; text-decoration: line-through; }
        .diff-new { color: green; }
        pre { background: #eee; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <nav><a href="/entries">🏠 Home</a></nav>
        <hr>
        {{ content }}
    </div>
</body>
</html>
"""

# --- Routes ---

@app.get("/entries", response_class=HTMLResponse)
async def list_entries():
    with get_db() as conn:
        rows = conn.execute("SELECT id, title FROM entries").fetchall()
    
    links = "".join([f'<li><a href="/entries/{row["id"]}">{row["title"]}</a></li>' for row in rows])
    body = f"<h1>Wiki Entries</h1><ul>{links}</ul>"
    if not links:
        body += "<p>No entries found.</p>"
    
    body += '<hr><h3>Create New Entry</h3><form action="/entries" method="post" enctype="application/json">'
    # Note: Standard HTML forms don't send JSON. For the sake of the OpenAPI spec (POST JSON), 
    # we'll provide a simple HTML form that we'll handle or just a note.
    # To strictly follow the OpenAPI spec, the client should send JSON.
    body += '<p>Use the API /docs to create entries via JSON.</p></div>'
    
    return render_wiki_html(HTML_LAYOUT, title="Home", content=body)

@app.post("/entries", status_code=201, response_model=Entry)
async def create_entry(entry: NewEntry):
    entry_id = str(len(get_db().execute("SELECT id FROM entries").fetchall()) + 1)
    now = datetime.datetime.utcnow()
    
    with get_db() as conn:
        conn.execute(
            "INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
            (entry_id, entry.title, entry.content, entry.createdBy, now)
        )
        conn.execute(
            "INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)",
            (entry_id, entry.content, entry.createdBy, "Initial creation", now)
        )
        conn.commit()
    
    return Entry(id=entry_id, title=entry.title, content=entry.content, lastModifiedBy=entry.createdBy, lastModifiedAt=now)

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    with get_db() as conn:
        entry = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        contributors = conn.execute("SELECT DISTINCT modified_by FROM edits WHERE entry_id = ?", (entryId,)).fetchall()
        contrib_list = ", ".join([c["modified_by"] for c in contributors])

    body = f"<h1>{entry['title']}</h1>"
    body += f"<div class='meta'>Last modified by {entry['last_modified_by']} on {entry['last_modified_at']}<br>"
    body += f"Contributors: {contrib_list}</div>"
    body += f"<div>{entry['content']}</div>"
    body += f'<hr><p><a href="/entries/{entryId}/edits">View History</a></p>'
    
    return render_wiki_html(HTML_LAYOUT, title=entry['title'], content=body)

@app.put("/entries/{entryId}", response_model=Entry)
async def update_entry(entryId: str, update: UpdateEntry):
    with get_db() as conn:
        entry = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        now = datetime.datetime.utcnow()
        conn.execute(
            "UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
            (update.content, update.modifiedBy, now, entryId)
        )
        conn.execute(
            "INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)",
            (entryId, update.content, update.modifiedBy, update.summary, now)
        )
        conn.commit()
        
        updated = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        return Entry(
            id=updated["id"], 
            title=updated["title"], 
            content=updated["content"], 
            lastModifiedBy=updated["last_modified_by"], 
            lastModifiedAt=updated["last_modified_at"]
        )

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    with get_db() as conn:
        entry = conn.execute("SELECT title FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        edits = conn.execute("SELECT * FROM edits WHERE entry_id = ? ORDER BY modified_at ASC", (entryId,)).fetchall()

    body = f"<h1>Edit History: {entry['title']}</h1>"
    
    prev_content = None
    for edit in edits:
        diff = ""
        if prev_content is not None:
            # Simple diff: just show old vs new
            diff = f"<pre><span class='diff-old'>- {prev_content}</span><br><span class='diff-new'>+ {edit['content']}</span></pre>"
        else:
            diff = f"<pre>{edit['content']}</pre>"
            
        body += f"""
        <div class="edit-item">
            <strong>{edit['modified_by']}</strong> ({edit['modified_at']})<br>
            <em>Summary: {edit['summary']}</em>
            {diff}
        </div>
        """
        prev_content = edit['content']

    return render_wiki_html(HTML_LAYOUT, title=f"History - {entry['title']}", content=body)

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=5000)