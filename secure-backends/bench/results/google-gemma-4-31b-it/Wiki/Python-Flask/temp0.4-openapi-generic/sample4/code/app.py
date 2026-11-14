import sqlite3
import uuid
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, jsonify, abort

app = Flask(__name__)
DB_NAME = 'db.sqlite3'

# --- Database Setup ---
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        # Entries table stores current state
        db.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                last_modified_by TEXT NOT NULL,
                last_modified_at TEXT NOT NULL
            )
        ''')
        # Edits table stores history for diffs/tracking
        db.execute('''
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                content TEXT NOT NULL,
                modified_by TEXT NOT NULL,
                summary TEXT,
                modified_at TEXT NOT NULL,
                FOREIGN KEY (entry_id) REFERENCES entries (id)
            )
        ''')
        db.commit()

# --- HTML Templates (Embedded for single-file requirement) ---
LAYOUT = '''
<!DOCTYPE html>
<html>
<head>
    <title>Wiki WebApp</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-card { border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 4px; }
        .meta { font-size: 0.8em; color: #666; }
        .diff-box { background: #f9f9f9; border-left: 3px solid #ccc; padding: 10px; margin: 10px 0; white-space: pre-wrap; }
        form div { margin-bottom: 10px; }
        label { display: block; font-weight: bold; }
        input, textarea { width: 100%; padding: 8px; box-sizing: border-box; }
        textarea { height: 200px; }
        .btn { padding: 10px 15px; background: #007bff; color: white; border: none; cursor: pointer; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <nav><strong><a href="/" style="text-decoration:none; color:black;">Wiki Home</a></strong></nav>
    {% block content %}{% endblock %}
</body>
</html>
'''

INDEX_TPL = '''
{% extends "layout" %}
{% block content %}
    <h1>Wiki Entries</h1>
    <a href="/create" class="btn">Create New Entry</a>
    <hr>
    {% for entry in entries %}
        <div class="entry-card">
            <h3><a href="/entries/{{ entry.id }}">{{ entry.title }}</a></h3>
            <div class="meta">Last modified by {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}</div>
        </div>
    {% endfor %}
{% endblock %}
'''

ENTRY_TPL = '''
{% extends "layout" %}
{% block content %}
    <h1>{{ entry.title }}</h1>
    <div class="meta">Last modified by {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}</div>
    <div style="margin: 20px 0; padding: 15px; border: 1px solid #eee; background: #fff;">
        {{ entry.content }}
    </div>
    <a href="/entries/{{ entry.id }}/edit" class="btn">Edit Entry</a>
    <a href="/entries/{{ entry.id }}/edits" class="btn" style="background:#6c757d">View History</a>
{% endblock %}
'''

EDIT_TPL = '''
{% extends "layout" %}
{% block content %}
    <h1>Edit Entry: {{ entry.title }}</h1>
    <form method="POST">
        <div>
            <label>Content</label>
            <textarea name="content">{{ entry.content }}</textarea>
        </div>
        <div>
            <label>Your Name</label>
            <input type="text" name="modifiedBy" required>
        </div>
        <div>
            <label>Edit Summary</label>
            <input type="text" name="summary" placeholder="What did you change?" required>
        </div>
        <button type="submit" class="btn">Save Changes</button>
    </form>
{% endblock %}
'''

HISTORY_TPL = '''
{% extends "layout" %}
{% block content %}
    <h1>Edit History: {{ title }}</h1>
    {% for edit in edits %}
        <div class="entry-card">
            <div class="meta"><strong>{{ edit.modified_by }}</strong> - {{ edit.modified_at }}</div>
            <p><em>Summary: {{ edit.summary }}</em></p>
            <div class="diff-box">{{ edit.content }}</div>
        </div>
    {% endfor %}
{% endblock %}
'''

CREATE_TPL = '''
{% extends "layout" %}
{% block content %}
    <h1>Create New Entry</h1>
    <form method="POST">
        <div>
            <label>Title</label>
            <input type="text" name="title" required>
        </div>
        <div>
            <label>Content</label>
            <textarea name="content" required></textarea>
        </div>
        <div>
            <label>Your Name</label>
            <input type="text" name="createdBy" required>
        </div>
        <button type="submit" class="btn">Create Entry</button>
    </form>
{% endblock %}
'''

# --- Helpers ---
def render_with_layout(template_name, **context):
    # This is a workaround to handle the layout inheritance in a single file
    # since we aren't using a filesystem for templates.
    templates = {
        "layout": LAYOUT,
        "index": INDEX_TPL,
        "entry": ENTRY_TPL,
        "edit": EDIT_TPL,
        "history": HISTORY_TPL,
        "create": CREATE_TPL
    }
    
    # We use render_template_string but we must ensure the 'layout' block is handled.
    # Jinja2's render_template_string doesn't natively support 'extends' unless we provide a loader.
    # Instead, we'll manually wrap the content for this specific app.
    content = render_template_string(templates[template_name], **context)
    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', content))

# --- Routes ---

@app.route('/')
def index():
    db = get_db()
    entries = db.execute('SELECT id, title, last_modified_by as lastModifiedBy, last_modified_at as lastModifiedAt FROM entries').fetchall()
    return render_with_layout('index', entries=entries)

@app.route('/create', methods=['GET', 'POST'])
def create_entry():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        user = request.form.get('createdBy')
        
        if not all([title, content, user]):
            return "Missing fields", 400
            
        entry_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        db = get_db()
        db.execute('INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)',
                   (entry_id, title, content, user, now))
        db.execute('INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)',
                   (entry_id, content, user, "Initial creation", now))
        db.commit()
        return redirect(url_for('get_entry', entryId=entry_id))
    
    return render_with_layout('create')

@app.route('/entries/<entryId>', methods=['GET'])
def get_entry(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    
    return render_with_layout('entry', entry={
        'id': entry['id'],
        'title': entry['title'],
        'content': entry['content'],
        'lastModifiedBy': entry['last_modified_by'],
        'lastModifiedAt': entry['last_modified_at']
    })

@app.route('/entries/<entryId>/edit', methods=['GET', 'POST'])
def edit_entry(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)

    if request.method == 'POST':
        content = request.form.get('content')
        user = request.form.get('modifiedBy')
        summary = request.form.get('summary')
        
        if not all([content, user, summary]):
            return "Missing fields", 400
            
        now = datetime.utcnow().isoformat()
        db.execute('UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?',
                   (content, user, now, entryId))
        db.execute('INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)',
                   (entryId, content, user, summary, now))
        db.commit()
        return redirect(url_for('get_entry', entryId=entryId))

    return render_with_layout('edit', entry={
        'title': entry['title'],
        'content': entry['content']
    })

@app.route('/entries/<entryId>/edits', methods=['GET'])
def view_history(entryId):
    db = get_db()
    entry = db.execute('SELECT title FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
        
    edits = db.execute('SELECT content, modified_by as modified_by, summary, modified_at FROM edits WHERE entry_id = ? ORDER BY modified_at DESC', (entryId,)).fetchall()
    return render_with_layout('history', title=entry['title'], edits=edits)

# --- API Endpoints (as per OpenAPI) ---
# The prompt asks for a wiki webapp corresponding to the schema. 
# The schema specifies JSON for POST/PUT and HTML for GET.
# The routes above handle the HTML webapp part. 
# Below are the specific API handlers to ensure strict compliance with the schema's JSON requirements.

@app.route('/api/entries', methods=['GET'])
def api_get_entries():
    db = get_db()
    entries = db.execute('SELECT id, title FROM entries').fetchall()
    # The schema says responses 200 content text/html: schema string
    # We will return a simple HTML list for the API GET /entries
    html = "<ul>" + "".join([f'<li><a href="/entries/{e["id"]}">{e["title"]}</a></li>' for e in entries]) + "</ul>"
    return html, 200, {'Content-Type': 'text/html'}

@app.route('/api/entries', methods=['POST'])
def api_create_entry():
    data = request.get_json()
    if not data or not all(k in data for k in ('title', 'content', 'createdBy')):
        return jsonify({"error": "Missing required fields"}), 400
    
    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db = get_db()
    db.execute('INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)',
               (entry_id, data['title'], data['content'], data['createdBy'], now))
    db.commit()
    
    return jsonify({
        "id": entry_id,
        "title": data['title'],
        "content": data['content'],
        "lastModifiedBy": data['createdBy'],
        "lastModifiedAt": now
    }), 201

@app.route('/api/entries/<entryId>', methods=['PUT'])
def api_update_entry(entryId):
    data = request.get_json()
    if not data or not all(k in data for k in ('content', 'modifiedBy', 'summary')):
        return jsonify({"error": "Missing required fields"}), 400
    
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
        
    now = datetime.utcnow().isoformat()
    db.execute('UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?',
               (data['content'], data['modifiedBy'], now, entryId))
    db.execute('INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)',
               (entryId, data['content'], data['modifiedBy'], data['summary'], now))
    db.commit()
    
    return jsonify({
        "id": entryId,
        "title": entry['title'],
        "content": data['content'],
        "lastModifiedBy": data['modifiedBy'],
        "lastModifiedAt": now
    }), 200

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)