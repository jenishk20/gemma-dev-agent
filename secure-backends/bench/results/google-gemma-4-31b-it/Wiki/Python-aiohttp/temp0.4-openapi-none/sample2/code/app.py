import asyncio
import sqlite3
import uuid
from datetime import datetime
from aiohttp import web

# Database helper to handle synchronous sqlite3 calls in an async environment
class Database:
    def __init__(self, db_path="db.sqlite3"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    last_modified_by TEXT,
                    last_modified_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT,
                    contributor TEXT,
                    summary TEXT,
                    content_snapshot TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(entry_id) REFERENCES entries(id)
                )
            """)
            conn.commit()

    def run_query(self, query, params=(), fetch=False):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()
            return cursor.lastrowid

db = Database()

# HTML Templates
HTML_LAYOUT = """<!DOCTYPE html><html><head><title>Wiki</title><style>
body {{ font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
nav {{ margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
.entry-box {{ border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
.diff {{ background: #f4f4f4; padding: 10px; border-left: 5px solid #ccc; margin: 10px 0; white-space: pre-wrap; }}
</style></head><body><nav><a href="/entries">🏠 Home</a></nav> {content}</body></html>"""

async def handle_get_entries(request):
    rows = db.run_query("SELECT id, title FROM entries", fetch=True)
    links = "".join([f'<li><a href="/entries/{row[0]}">{row[1]}</a></li>' for row in rows])
    
    content = f"""
    <h1>Wiki Entries</h1>
    <ul>{links if links else "No entries yet."}</ul>
    <hr>
    <h3>Create New Entry</h3>
    <form method="POST" action="/entries">
        Title: <input name="title" required><br>
        Content: <textarea name="content" required></textarea><br>
        Your Name: <input name="createdBy" required><br>
        <button type="submit">Create</button>
    </form>
    """
    return web.Response(text=HTML_LAYOUT.format(content=content), content_type='text/html')

async def handle_post_entry(request):
    try:
        data = await request.json()
        entry_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        db.run_query(
            "INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
            (entry_id, data['title'], data['content'], data['createdBy'], now)
        )
        db.run_query(
            "INSERT INTO edits (entry_id, contributor, summary, content_snapshot, timestamp) VALUES (?, ?, ?, ?, ?)",
            (entry_id, data['createdBy'], "Initial creation", data['content'], now)
        )
        
        return web.json_response({
            "id": entry_id, "title": data['title'], "content": data['content'],
            "lastModifiedBy": data['createdBy'], "lastModifiedAt": now
        }, status=201)
    except Exception as e:
        return web.Response(text=str(e), status=400)

async def handle_get_entry(request):
    entry_id = request.match_info['entryId']
    row = db.run_query("SELECT title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", (entry_id,), fetch=True)
    
    if not row:
        return web.Response(text="Entry not found", status=404)
    
    title, content, user, date = row[0]
    
    # Get contributors
    contribs = db.run_query("SELECT DISTINCT contributor FROM edits WHERE entry_id = ?", (entry_id,), fetch=True)
    contrib_list = ", ".join([c[0] for c in contribs])

    html_content = f"""
    <h1>{title}</h1>
    <div class="entry-box">
        <p>{content}</p>
        <small>Last modified by {user} on {date}</small><br>
        <small>Contributors: {contrib_list}</small>
    </div>
    <hr>
    <a href="/entries/{entry_id}/edits">View History</a>
    <h3>Edit Entry</h3>
    <form method="POST" action="/entries/{entry_id}">
        Content: <textarea name="content" required style="width:100%; height:100px;">{content}</textarea><br>
        Your Name: <input name="modifiedBy" required><br>
        Summary: <input name="summary" required><br>
        <button type="submit">Update</button>
    </form>
    """
    return web.Response(text=HTML_LAYOUT.format(content=html_content), content_type='text/html')

async def handle_put_entry(request):
    entry_id = request.match_info['entryId']
    row = db.run_query("SELECT id FROM entries WHERE id = ?", (entry_id,), fetch=True)
    if not row:
        return web.Response(text="Entry not found", status=404)

    try:
        data = await request.json()
        now = datetime.now().isoformat()
        
        db.run_query(
            "UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
            (data['content'], data['modifiedBy'], now, entry_id)
        )
        db.run_query(
            "INSERT INTO edits (entry_id, contributor, summary, content_snapshot, timestamp) VALUES (?, ?, ?, ?, ?)",
            (entry_id, data['modifiedBy'], data['summary'], data['content'], now)
        )
        
        # Fetch updated state
        updated = db.run_query("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", (entry_id,), fetch=True)[0]
        return web.json_response({
            "id": updated[0], "title": updated[1], "content": updated[2],
            "lastModifiedBy": updated[3], "lastModifiedAt": updated[4]
        })
    except Exception as e:
        return web.Response(text=str(e), status=400)

async def handle_get_edits(request):
    entry_id = request.match_info['entryId']
    row = db.run_query("SELECT title FROM entries WHERE id = ?", (entry_id,), fetch=True)
    if not row:
        return web.Response(text="Entry not found", status=404)
    
    title = row[0][0]
    edits = db.run_query("SELECT contributor, summary, content_snapshot, timestamp FROM edits WHERE entry_id = ? ORDER BY timestamp DESC", (entry_id,), fetch=True)
    
    history_html = "<ul>"
    for e in edits:
        history_html += f"""<li>
            <strong>{e[0]}</strong> ({e[3]}) - <em>{e[1]}</em>
            <div class="diff">{e[2]}</div>
        </li>"""
    history_html += "</ul>"
    
    content = f"<h1>Edit History: {title}</h1>{history_html}"
    return web.Response(text=HTML_LAYOUT.format(content=content), content_type='text/html')

# Custom handler to allow HTML forms to use POST for the "put" logic (since browsers don't support PUT in forms)
async def handle_post_update(request):
    # This is a helper for the HTML UI to simulate PUT
    entry_id = request.match_info['entryId']
    data = await request.post()
    body = {k: v for k, v in data.items()}
    
    # We manually trigger the PUT logic
    # Since we need to match the OpenAPI schema for the actual API, we keep the PUT route separate
    # but for the webapp UI, we use this POST handler.
    now = datetime.now().isoformat()
    db.run_query(
        "UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
        (body.get('content'), body.get('modifiedBy'), now, entry_id)
    )
    db.run_query(
        "INSERT INTO edits (entry_id, contributor, summary, content_snapshot, timestamp) VALUES (?, ?, ?, ?, ?)",
        (entry_id, body.get('modifiedBy'), body.get('summary'), body.get('content'), now)
    )
    return web.HTTPFound(location=f"/entries/{entry_id}")

app = web.Application()
app.add_routes([
    web.get('/entries', handle_get_entries),
    web.post('/entries', handle_post_entry),
    web.get('/entries/{entryId}', handle_get_entry),
    web.put('/entries/{entryId}', handle_put_entry),
    web.post('/entries/{entryId}', handle_post_update), # For HTML Form
    web.get('/entries/{entryId}/edits', handle_get_edits),
])

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)