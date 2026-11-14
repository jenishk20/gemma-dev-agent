import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

app = FastAPI(title="Wiki API")
templates = Jinja2Templates(directory="templates") # We will simulate templates via strings since we must be in one file

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
    summary: Optional[str] = "No summary provided"

# --- HTML Templates (In-memory) ---
# Since we must be in one file and cannot create a /templates folder, 
# we use a custom Jinja2 loader or just return HTMLResponse directly.
# For simplicity and robustness in a single-file constraint, we'll use f-strings for HTML.

def layout(content: str, title: str = "Wiki"):
    return f"""
    <html>
        <head><title>{title}</title><style>
            body {{ font-family: sans-serif; margin: 40px; line-height: 1.6; }}
            nav {{ margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
            .entry-box {{ border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
            .diff {{ background: #f4f4f4; padding: 10px; border-left: 3px solid #ccc; white-space: pre-wrap; }}
            .edit-item {{ margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        </style></head>
        <body>
            <nav><a href="/entries">🏠 Home</a> | <a href="/create">➕ New Entry</a></nav>
            {content}
        </body>
    </html>
    """

# --- Routes ---

@app.get("/entries", response_class=HTMLResponse)
async def get_entries():
    with get_db() as conn:
        cursor = conn.execute("SELECT id, title FROM entries")
        rows = cursor.fetchall()
    
    links = "".join([f"<li><a href='/entries/{row['id']}'>{row['title']}</a></li>" for row in rows])
    content = f"<h1>Wiki Entries</h1><ul>{links if links else '<li>No entries yet.</li>'}</ul>"
    return HTMLResponse(content=layout(content))

@app.get("/create", response_class=HTMLResponse)
async def create_page():
    html = """
    <h1>Create New Entry</h1>
    <form method="post" action="/entries">
        <input type="text" name="title" placeholder="Title" required><br><br>
        <textarea name="content" placeholder="Content" rows="10" cols="50" required></textarea><br><br>
        <input type="text" name="createdBy" placeholder="Your Name" required><br><br>
        <button type="submit">Save Entry</button>
    </form>
    """
    # Note: The OpenAPI says POST /entries takes JSON. To support the HTML form, 
    # we'd need a separate route or handle multipart. 
    # For strict adherence to the OpenAPI schema (JSON), we provide a simple JSON-based UI or just the API.
    # However, to make it a "webapp", I'll provide a simple HTML form that sends JSON via JS.
    html_with_js = f"""
    {html}
    <script>
    document.querySelector('form').onsubmit = async (e) => {{
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());
        const res = await fetch('/entries', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(data)
        }});
        if (res.ok) window.location.href = '/entries';
    }};
    </script>
    """
    return HTMLResponse(content=layout(html_with_js))

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

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        contributors = conn.execute("SELECT DISTINCT modifiedBy FROM edits WHERE entryId = ?", (entryId,)).fetchall()
        contrib_list = ", ".join([c['modifiedBy'] for c in contributors])

    content = f"""
    <div class="entry-box">
        <h1>{row['title']}</h1>
        <p>{row['content']}</p>
        <hr>
        <small>Last modified by: {row['lastModifiedBy']} on {row['lastModifiedAt']}</small><br>
        <small>Contributors: {contrib_list}</small>
    </div>
    <br>
    <a href="/entries/{entryId}/edit">📝 Edit this page</a> | 
    <a href="/entries/{entryId}/edits">📜 View History</a>
    """
    return HTMLResponse(content=layout(content))

@app.get("/entries/{entryId}/edit", response_class=HTMLResponse)
async def edit_page(entryId: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
    
    html = f"""
    <h1>Edit: {row['title']}</h1>
    <form id="editForm">
        <textarea name="content" rows="10" cols="50" required>{row['content']}</textarea><br><br>
        <input type="text" name="modifiedBy" placeholder="Your Name" required><br><br>
        <input type="text" name="summary" placeholder="What did you change?"><br><br>
        <button type="submit">Save Changes</button>
    </form>
    <script>
    document.getElementById('editForm').onsubmit = async (e) => {{
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());
        const res = await fetch('/entries/{entryId}', {{
            method: 'PUT',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(data)
        }});
        if (res.ok) window.location.href = '/entries/{entryId}';
    }};
    </script>
    """
    return HTMLResponse(content=layout(html))

@app.put("/entries/{entryId}")
async def update_entry(entryId: str, update: UpdateEntry):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?",
            (update.content, update.modifiedBy, now, entryId)
        )
        conn.execute(
            "INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)",
            (entryId, update.content, update.modifiedBy, update.summary, now)
        )
        conn.commit()
        
        updated = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        return {
            "id": updated['id'], 
            "title": updated['title'], 
            "content": updated['content'], 
            "lastModifiedBy": updated['lastModifiedBy'], 
            "lastModifiedAt": updated['lastModifiedAt']
        }

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    with get_db() as conn:
        # Check if entry exists
        entry = conn.execute("SELECT id FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        edits = conn.execute("SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", (entryId,)).fetchall()
    
    history_html = ""
    for i in range(len(edits)):
        edit = edits[i]
        # Simple diff: just show the content of that version
        history_html += f"""
        <div class="edit-item">
            <strong>{edit['modifiedBy']}</strong> - {edit['modifiedAt']}<br>
            <em>Summary: {edit['summary']}</em>
            <div class="diff">{edit['content']}</div>
        </div>
        """
    
    content = f"<h1>Edit History</h1>{history_html if history_html else '<p>No edits found.</p>'}"
    return HTMLResponse(content=layout(content))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)