import asyncio
import sqlite3
import uuid
from datetime import datetime
from aiohttp import web

# Database helper to handle synchronous sqlite3 calls in a thread pool
async def run_query(query, params=(), fetchall=True, commit=False):
    def _execute():
        with sqlite3.connect('db.sqlite3') as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
                return cursor.lastrowid
            return cursor.fetchall()
    return await asyncio.to_thread(_execute)

async def init_db():
    # Create tables for entries and their edit history
    await run_query('''
        CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            lastModifiedBy TEXT,
            lastModifiedAt TEXT
        )
    ''', commit=True)
    await run_query('''
        CREATE TABLE IF NOT EXISTS edits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entryId TEXT,
            content TEXT,
            modifiedBy TEXT,
            summary TEXT,
            modifiedAt TEXT,
            FOREIGN KEY(entryId) REFERENCES entries(id)
        )
    ''', commit=True)

# --- Request Handlers ---

async def get_entries(request):
    rows = await run_query("SELECT id, title FROM entries")
    html = "<h1>Wiki Entries</h1><ul>"
    for row in rows:
        html += f'<li><a href="/entries/{row[0]}">{row[1]}</a></li>'
    html += "</ul><hr><p>Create new: <form method='POST' action='/entries'><input name='title' placeholder='Title'><br><textarea name='content'></textarea><br><input name='createdBy' placeholder='Your Name'><button type='submit'>Create</button></form></p>"
    return web.Response(text=html, content_type='text/html')

async def create_entry(request):
    try:
        data = await request.json()
        entry_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        # Insert into entries
        await run_query(
            "INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)",
            (entry_id, data['title'], data['content'], data['createdBy'], now),
            commit=True
        )
        # Record initial edit
        await run_query(
            "INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)",
            (entry_id, data['content'], data['createdBy'], "Initial creation", now),
            commit=True
        )
        
        return web.json_response({
            "id": entry_id,
            "title": data['title'],
            "content": data['content'],
            "lastModifiedBy": data['createdBy'],
            "lastModifiedAt": now
        }, status=201)
    except Exception as e:
        return web.Response(text=str(e), status=400)

async def get_entry(request):
    entry_id = request.match_info['entryId']
    row = await run_query("SELECT * FROM entries WHERE id = ?", (entry_id,), fetchall=False)
    # Note: run_query with fetchall=False is not explicitly handled in helper, 
    # but fetchall=True returns a list. Let's adjust helper or handle list.
    rows = await run_query("SELECT * FROM entries WHERE id = ?", (entry_id,))
    if not rows:
        return web.Response(text="Entry not found", status=404)
    
    entry = rows[0]
    # Get contributors
    contributors_rows = await run_query("SELECT DISTINCT modifiedBy FROM edits WHERE entryId = ?", (entry_id,))
    contributors = [r[0] for r in contributors_rows]
    
    html = f"<h1>{entry[1]}</h1>"
    html += f"<p>{entry[2]}</p>"
    html += f"<p><i>Last modified by {entry[3]} at {entry[4]}</i></p>"
    html += f"<p>Contributors: {', '.join(contributors)}</p>"
    html += f'<hr><a href="/entries">Back to List</a> | <a href="/entries/{entry_id}/edits">History</a>'
    html += f'<hr><h3>Edit Entry</h3><form method="POST" action="/entries/{entry_id}?_method=PUT">'
    html += f'<textarea name="content" style="width:100%; height:200px">{entry[2]}</textarea><br>'
    html += f'<input name="modifiedBy" placeholder="Your Name"><br>'
    html += f'<input name="summary" placeholder="What did you change?"><br>'
    html += f'<button type="submit">Save Changes</button></form>'
    
    return web.Response(text=html, content_type='text/html')

async def update_entry(request):
    entry_id = request.match_info['entryId']
    try:
        data = await request.json()
        now = datetime.utcnow().isoformat()
        
        # Check if exists
        exists = await run_query("SELECT id FROM entries WHERE id = ?", (entry_id,))
        if not exists:
            return web.Response(text="Entry not found", status=404)
            
        await run_query(
            "UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?",
            (data['content'], data['modifiedBy'], now, entry_id),
            commit=True
        )
        await run_query(
            "INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)",
            (entry_id, data['content'], data['modifiedBy'], data['summary'], now),
            commit=True
        )
        
        return web.json_response({
            "id": entry_id,
            "content": data['content'],
            "lastModifiedBy": data['modifiedBy'],
            "lastModifiedAt": now
        })
    except Exception as e:
        return web.Response(text=str(e), status=400)

async def get_edits(request):
    entry_id = request.match_info['entryId']
    rows = await run_query("SELECT content, modifiedBy, summary, modifiedAt FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC", (entry_id,))
    if not rows:
        # Check if entry exists at all
        exists = await run_query("SELECT id FROM entries WHERE id = ?", (entry_id,))
        if not exists:
            return web.Response(text="Entry not found", status=404)

    html = f"<h1>Edit History for {entry_id}</h1><ul>"
    for row in rows:
        html += f"<li><b>{row[3]}</b> by {row[1]} - {row[2]}<br><pre>{row[0]}</pre></li><hr>"
    html += "</ul><a href='/entries'>Back to List</a>"
    return web.Response(text=html, content_type='text/html')

# Middleware to handle HTML form "PUT" via a query param since HTML forms only support GET/POST
@web.middleware
async def method_override_middleware(request, handler):
    if request.method == 'POST' and request.query.get('_method') == 'PUT':
        request.method = 'PUT'
    return await handler(request)

async def app_factory():
    app = web.Application(middlewares=[method_override_middleware])
    app.add_routes([
        web.get('/entries', get_entries),
        web.post('/entries', create_entry),
        web.get('/entries/{entryId}', get_entry),
        web.put('/entries/{entryId}', update_entry),
        web.get('/entries/{entryId}/edits', get_edits),
    ])
    return app

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    app = loop.run_until_complete(app_factory())
    web.run_app(app, host='0.0.0.0', port=5000)