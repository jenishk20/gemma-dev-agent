import asyncio
import sqlite3
import uuid
from datetime import datetime
from aiohttp import web

# Database setup
DB_NAME = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
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

# Helper for DB queries to avoid blocking the event loop too much
# (In a production app, we'd use a thread pool or aiosqlite)
def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute(query, params)
        if commit:
            conn.commit()
            return None
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
        return None

# HTML Templates
HTML_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki</title>
    <style>
        body {{ font-family: sans-serif; margin: 40px; line-height: 1.6; }}
        .container {{ max-width: 800px; margin: auto; }}
        .entry-box {{ border: 1px solid #ccc; padding: 20px; margin-bottom: 20px; }}
        .meta {{ font-size: 0.8em; color: #666; }}
        nav {{ margin-bottom: 20px; }}
        textarea {{ width: 100%; height: 200px; }}
        .diff {{ background: #f4f4f4; padding: 10px; border-left: 3px solid #ccc; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="container">
        <nav><a href="/entries">🏠 Home</a> | <a href="/create">➕ New Entry</a></nav>
        {content}
    </div>
</body>
</html>
"""

async def get_entries(request):
    rows = db_query("SELECT id, title FROM entries", fetchall=True)
    links = "".join([f'<li><a href="/entries/{row[0]}">{row[1]}</a></li>' for row in rows])
    content = f"<h1>Wiki Entries</h1><ul>{links if links else 'No entries yet.'}</ul>"
    return web.Response(text=HTML_LAYOUT.format(content=content), content_type='text/html')

async def create_entry_page(request):
    # Simple HTML form for the POST request
    content = """
    <h1>Create New Entry</h1>
    <form method="POST" action="/entries">
        <input type="text" name="title" placeholder="Title" required style="width:100%; margin-bottom:10px;"><br>
        <textarea name="content" placeholder="Content" required></textarea><br>
        <input type="text" name="createdBy" placeholder="Your Name" required style="width:100%; margin-bottom:10px;"><br>
        <button type="submit">Save Entry</button>
    </form>
    """
    return web.Response(text=HTML_LAYOUT.format(content=content), content_type='text/html')

async def post_entry(request):
    try:
        data = await request.json()
    except:
        # Handle form-data if the user uses the HTML page instead of JSON
        data = await request.post()
        data = {k: v for k, v in data.items()}

    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    db_query("INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)",
             (entry_id, data['title'], data['content'], data['createdBy'], now), commit=True)
    
    db_query("INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)",
             (entry_id, data['content'], data['createdBy'], "Initial creation", now), commit=True)
    
    return web.json_response({"id": entry_id, "title": data['title'], "content": data['content'], 
                             "lastModifiedBy": data['createdBy'], "lastModifiedAt": now}, status=201)

async def get_entry(request):
    entry_id = request.match_info['entryId']
    row = db_query("SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?", (entry_id,), fetchone=True)
    
    if not row:
        return web.Response(status=404, text="Entry not found")
    
    content = f"""
    <h1>{row[1]}</h1>
    <div class="entry-box">{row[2]}</div>
    <div class="meta">Last edited by {row[3]} on {row[4]}</div>
    <hr>
    <a href="/entries/{row[0]}/edit">Edit this page</a> | <a href="/entries/{row[0]}/edits">View History</a>
    """
    return web.Response(text=HTML_LAYOUT.format(content=content), content_type='text/html')

async def edit_entry_page(request):
    entry_id = request.match_info['entryId']
    row = db_query("SELECT title, content FROM entries WHERE id = ?", (entry_id,), fetchone=True)
    if not row: return web.Response(status=404)
    
    content = f"""
    <h1>Edit: {row[0]}</h1>
    <form method="POST" action="/entries/{entry_id}">
        <textarea name="content" required>{row[1]}</textarea><br>
        <input type="text" name="modifiedBy" placeholder="Your Name" required style="width:100%; margin-bottom:10px;"><br>
        <input type="text" name="summary" placeholder="What did you change?" required style="width:100%; margin-bottom:10px;"><br>
        <button type="submit">Save Changes</button>
    </form>
    """
    return web.Response(text=HTML_LAYOUT.format(content=content), content_type='text/html')

async def update_entry(request):
    entry_id = request.match_info['entryId']
    try:
        data = await request.json()
    except:
        data = await request.post()
        data = {k: v for k, v in data.items()}

    row = db_query("SELECT id FROM entries WHERE id = ?", (entry_id,), fetchone=True)
    if not row:
        return web.Response(status=404, text="Entry not found")

    now = datetime.utcnow().isoformat()
    db_query("UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?",
             (data['content'], data['modifiedBy'], now, entry_id), commit=True)
    
    db_query("INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)",
             (entry_id, data['content'], data['modifiedBy'], data['summary'], now), commit=True)
    
    return web.json_response({"id": entry_id, "content": data['content'], "lastModifiedBy": data['modifiedBy'], "lastModifiedAt": now})

async def get_edits(request):
    entry_id = request.match_info['entryId']
    row = db_query("SELECT title FROM entries WHERE id = ?", (entry_id,), fetchone=True)
    if not row:
        return web.Response(status=404, text="Entry not found")
    
    edits = db_query("SELECT content, modified_by, summary, modified_at FROM edits WHERE entry_id = ? ORDER BY modified_at DESC", (entry_id,), fetchall=True)
    
    history_html = f"<h1>History: {row[0]}</h1>"
    for e in edits:
        history_html += f"""
        <div class="entry-box">
            <div class="meta"><strong>{e[1]}</strong> - {e[3]}</div>
            <p><em>{e[2]}</em></p>
            <div class="diff">{e[0]}</div>
        </div>
        """
    
    return web.Response(text=HTML_LAYOUT.format(content=history_html), content_type='text/html')

app = web.Application()
app.add_routes([
    web.get('/entries', get_entries),
    web.post('/entries', post_entry),
    web.get('/create', create_entry_page),
    web.get('/entries/{entryId}', get_entry),
    web.put('/entries/{entryId}', update_entry),
    web.post('/entries/{entryId}', update_entry), # Support HTML form POST as PUT
    web.get('/entries/{entryId}/edit', edit_entry_page),
    web.get('/entries/{entryId}/edits', get_edits),
])

if __name__ == "__main__":
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)