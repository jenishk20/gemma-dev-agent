import asyncio
import sqlite3
import datetime
import uuid
from aiohttp import web

# Database Manager to handle SQLite operations asynchronously
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
                    content TEXT,
                    modified_by TEXT,
                    summary TEXT,
                    modified_at TEXT,
                    FOREIGN KEY(entry_id) REFERENCES entries(id)
                )
            """)
            conn.commit()

    def get_all_entries(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, title FROM entries")
            return cursor.fetchall()

    def create_entry(self, title, content, created_by):
        entry_id = str(uuid.uuid4())
        now = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
                (entry_id, title, content, created_by, now)
            )
            conn.execute(
                "INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)",
                (entry_id, content, created_by, "Initial creation", now)
            )
            conn.commit()
        return entry_id, title, content, created_by, now

    def get_entry(self, entry_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", (entry_id,))
            return cursor.fetchone()

    def update_entry(self, entry_id, content, modified_by, summary):
        now = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id FROM entries WHERE id = ?", (entry_id,))
            if not cursor.fetchone():
                return None
            
            conn.execute(
                "UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
                (content, modified_by, now, entry_id)
            )
            conn.execute(
                "INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)",
                (entry_id, content, modified_by, summary, now)
            )
            conn.commit()
            
            cursor = conn.execute("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", (entry_id,))
            return cursor.fetchone()

    def get_edits(self, entry_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT content, modified_by, summary, modified_at FROM edits WHERE entry_id = ? ORDER BY modified_at DESC", (entry_id,))
            return cursor.fetchall()

db = Database()

# Handlers
async def handle_get_entries(request):
    entries = db.get_all_entries()
    html = "<h1>Wiki Entries</h1><ul>"
    for eid, title in entries:
        html += f'<li><a href="/entries/{eid}">{title}</a></li>'
    html += "</ul><hr><p>Create new entry via POST /entries</p>"
    return web.Response(text=html, content_type='text/html')

async def handle_post_entry(request):
    try:
        data = await request.json()
        title = data['title']
        content = data['content']
        created_by = data['createdBy']
        
        eid, t, c, user, date = db.create_entry(title, content, created_by)
        
        return web.json_response({
            "id": eid, "title": t, "content": c, 
            "lastModifiedBy": user, "lastModifiedAt": date
        }, status=201)
    except Exception as e:
        return web.Response(text=str(e), status=400)

async def handle_get_entry(request):
    entry_id = request.match_info['entryId']
    row = db.get_entry(entry_id)
    if not row:
        return web.Response(text="Entry not found", status=404)
    
    eid, title, content, user, date = row
    html = f"<h1>{title}</h1>"
    html += f"<p>Last modified by {user} at {date}</p>"
    html += f"<div style='border:1px solid #ccc; padding:10px;'>{content}</div>"
    html += f"<p><a href='/entries/{eid}/edits'>View History</a> | <a href='/entries'>Back to List</a></p>"
    return web.Response(text=html, content_type='text/html')

async def handle_put_entry(request):
    entry_id = request.match_info['entryId']
    try:
        data = await request.json()
        content = data['content']
        modified_by = data['modifiedBy']
        summary = data.get('summary', 'No summary provided')
        
        updated = db.update_entry(entry_id, content, modified_by, summary)
        if not updated:
            return web.Response(text="Entry not found", status=404)
        
        eid, title, c, user, date = updated
        return web.json_response({
            "id": eid, "title": title, "content": c, 
            "lastModifiedBy": user, "lastModifiedAt": date
        })
    except Exception as e:
        return web.Response(text=str(e), status=400)

async def handle_get_edits(request):
    entry_id = request.match_info['entryId']
    row = db.get_entry(entry_id)
    if not row:
        return web.Response(text="Entry not found", status=404)
    
    edits = db.get_edits(entry_id)
    html = f"<h1>Edit History for {row[1]}</h1><ul>"
    for content, user, summary, date in edits:
        html += f"<li><b>{date}</b> by {user}: <i>{summary}</i><br><pre>{content}</pre></li><hr>"
    html += "</ul><a href='/entries'>Back to List</a>"
    return web.Response(text=html, content_type='text/html')

# App Setup
app = web.Application()
app.add_routes([
    web.get('/entries', handle_get_entries),
    web.post('/entries', handle_post_entry),
    web.get('/entries/{entryId}', handle_get_entry),
    web.put('/entries/{entryId}', handle_put_entry),
    web.get('/entries/{entryId}/edits', handle_get_edits),
])

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)