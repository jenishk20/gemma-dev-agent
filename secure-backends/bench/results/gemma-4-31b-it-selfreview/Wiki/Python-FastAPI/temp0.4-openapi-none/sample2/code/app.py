import sqlite3
import uuid
import html
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Wiki API")

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

# --- Security Helpers ---
def escape_html(text: str) -> str:
    """Escapes untrusted input to prevent XSS."""
    return html.escape(text)

# --- HTML Templates ---
def layout(content: str, title: str = "Wiki"):
    # Note: title is usually controlled by the dev, but we escape it for safety
    safe_title = escape_html(title)
    return f"""
    <html lang="en">
        <head><title>{safe_title}</title><style>
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
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT id, title FROM entries")
            rows = cursor.fetchall()
        
        links = "".join([f"<li><a href='/entries/{escape_html(row['id'])}'>{escape_html(row['title'])}</a></li>" for row in rows])
        content = f"<h1>Wiki Entries</h1><ul>{links if links else '<li style=\"color:gray\">No entries yet.</li>'}</ul>"
        return HTMLResponse(content=layout(content))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/create", response_class=HTMLResponse)
async def create_page():
    html_body = """
    <h1>Create New Entry</h1>
    <form id="createForm">
        <input type="text" name="title" placeholder="Title" required><br><br>
        <textarea name="content" placeholder="Content" rows="10" cols="50" required></textarea><br><br>
        <input type="text" name="createdBy" placeholder="Your Name" required><br><br>
        <button type="submit">Save Entry</button>
    </form>
    <script>
    document.getElementById('createForm').onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());
        const res = await fetch('/entries', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        if (res.ok) window.location.href = '/entries';
        else alert('Error creating entry');
    };
    </script>
    """
    return HTMLResponse(content=layout(html_body))

@app.post("/entries", status_code=201)
async def create_entry(entry: NewEntry):
    # Pydantic handles basic type validation. 
    # We use UUIDs for IDs to prevent ID enumeration/guessing.
    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    try:
        with get_db() as conn:
            # Parameterized queries prevent SQL Injection
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

@app.get("/entries/{entryId}", response_class=HTMLResponse)
async def get_entry(entryId: str):
    try:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Entry not found")
            
            contributors = conn.execute("SELECT DISTINCT modifiedBy FROM edits WHERE entryId = ?", (entryId,)).fetchall()
            contrib_list = ", ".join([escape_html(c['modifiedBy']) for c in contributors])

        # Escape all user-generated content to prevent XSS
        content = f"""
        <div class="entry-box">
            <h1>{escape_html(row['title'])}</h1>
            <p>{escape_html(row['content'])}</p>
            <hr>
            <small>Last modified by: {escape_html(row['lastModifiedBy'])} on {escape_html(row['lastModifiedAt'])}</small><br>
            <small>Contributors: {contrib_list}</small>
        </div>
        <br>
        <a href="/entries/{escape_html(entryId)}/edit">📝 Edit this page</a> | 
        <a href="/entries/{escape_html(entryId)}/edits">📜 View History</a>
        """
        return HTMLResponse(content=layout(content))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/entries/{entryId}/edit", response_class=HTMLResponse)
async def edit_page(entryId: str):
    try:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Entry not found")
        
        # We escape content inside the textarea. Note: HTML attributes need careful handling.
        safe_content = escape_html(row['content'])
        safe_id = escape_html(entryId)
        
        html_body = f"""
        <h1>Edit: {escape_html(row['title'])}</h1>
        <form id="editForm">
            <textarea name="content" rows="10" cols="50" required>{safe_content}</textarea><br><br>
            <input type="text" name="modifiedBy" placeholder="Your Name" required><br><br>
            <input type="text" name="summary" placeholder="What did you change?"><br><br>
            <button type="submit">Save Changes</button>
        </form>
        <script>
        document.getElementById('editForm').onsubmit = async (e) => {{
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());
            const res = await fetch('/entries/{safe_id}', {{
                method: 'PUT',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(data)
            }});
            if (res.ok) window.location.href = '/entries/{safe_id}';
            else alert('Error updating entry');
        }};
        </script>
        """
        return HTMLResponse(content=layout(html_body))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.put("/entries/{entryId}")
async def update_entry(entryId: str, update: UpdateEntry):
    try:
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
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/entries/{entryId}/edits", response_class=HTMLResponse)
async def get_edits(entryId: str):
    try:
        with get_db() as conn:
            entry = conn.execute("SELECT id FROM entries WHERE id = ?", (entryId,)).fetchone()
            if not entry:
                raise HTTPException(status_code=404, detail="Entry not found")
            
            edits = conn.execute("SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", (entryId,)).fetchall()
        
        history_html = ""
        for edit in edits:
            history_html += f"""
            <div class="edit-item">
                <strong>{escape_html(edit['modifiedBy'])}</strong> - {escape_html(edit['modifiedAt'])}<br>
                <em>Summary: {escape_html(edit['summary'] if edit['summary'] else "No summary")}</em>
                <div class="diff">{escape_html(edit['content'])}</div>
            </div>
            """
        
        content = f"<h1>Edit History</h1>{history_html if history_html else '<p>No edits found.</p>'}"
        return HTMLResponse(content=layout(content))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)