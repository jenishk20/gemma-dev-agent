import sqlite3
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, abort

app = Flask(__name__)

# Database initialization
def get_db():
    conn = sqlite3.connect('db.sqlite3')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                last_modified_by TEXT,
                last_modified_at TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT,
                contributor TEXT,
                content_snapshot TEXT,
                summary TEXT,
                timestamp TEXT,
                FOREIGN KEY(entry_id) REFERENCES entries(id)
            )
        ''')
        conn.commit()

init_db()

# HTML Templates
LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki App</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; max-width: 800px; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-box { border: 1px solid #ddd; padding: 20px; border-radius: 5px; }
        .meta { font-size: 0.8em; color: #666; margin-bottom: 20px; }
        .diff-box { background: #f9f9f9; border-left: 3px solid #ccc; padding: 10px; margin: 10px 0; white-space: pre-wrap; }
        form div { margin-bottom: 10px; }
        label { display: block; font-weight: bold; }
        input, textarea { width: 100%; padding: 8px; box-sizing: border-box; }
        textarea { height: 200px; }
        .btn { background: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 3px; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <nav>
        <a href="/">🏠 Home</a> | <a href="/create">➕ New Entry</a>
    </nav>
    {% block content %}{% endblock %}
</body>
</html>
"""

INDEX_TPL = """
{% extends "layout" %}
{% block content %}
<h1>Wiki Entries</h1>
<ul>
    {% for entry in entries %}
    <li><a href="/entries/{{ entry.id }}">{{ entry.title }}</a></li>
    {% endfor %}
</ul>
{% endblock %}
"""

ENTRY_TPL = """
{% extends "layout" %}
{% block content %}
<div class="entry-box">
    <h1>{{ entry.title }}</h1>
    <div class="meta">
        Last modified by {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}
    </div>
    <div class="content">{{ entry.content }}</div>
    <hr>
    <a href="/entries/{{ entry.id }}/edit" class="btn">Edit Page</a>
    <a href="/entries/{{ entry.id }}/edits" class="btn" style="background:#6c757d">View History</a>
</div>
{% endblock %}
"""

EDIT_TPL = """
{% extends "layout" %}
{% block content %}
<h1>Edit: {{ entry.title }}</h1>
<form method="POST">
    <div>
        <label>Contributor Name</label>
        <input type="text" name="modifiedBy" value="{{ entry.lastModifiedBy }}" required>
    </div>
    <div>
        <label>Edit Summary</label>
        <input type="text" name="summary" placeholder="What did you change?" required>
    </div>
    <div>
        <label>Content</label>
        <textarea name="content" required>{{ entry.content }}</textarea>
    </div>
    <button type="submit" class="btn">Save Changes</button>
</form>
{% endblock %}
"""

CREATE_TPL = """
{% extends "layout" %}
{% block content %}
<h1>Create New Entry</h1>
<form method="POST">
    <div>
        <label>Title</label>
        <input type="text" name="title" required>
    </div>
    <div>
        <label>Your Name</label>
        <input type="text" name="createdBy" required>
    </div>
    <div>
        <label>Content</label>
        <textarea name="content" required></textarea>
    </div>
    <button type="submit" class="btn">Create Entry</button>
</form>
{% endblock %}
"""

HISTORY_TPL = """
{% extends "layout" %}
{% block content %}
<h1>History: {{ title }}</h1>
{% for edit in edits %}
    <div class="diff-box">
        <strong>{{ edit.contributor }}</strong> - {{ edit.timestamp }}<br>
        <em>Summary: {{ edit.summary }}</em>
        <hr>
        {{ edit.content }}
    </div>
{% endfor %}
{% endblock %}
"""

# Template helper to handle the layout
@app.context_processor
def inject_layout():
    return dict(layout=LAYOUT)

@app.route('/layout') # Dummy route to satisfy Jinja's extends if needed, but we use render_template_string
def layout(): pass

def render_with_layout(template_str, **context):
    # Since we are using one file, we simulate the layout extension by replacing the block
    content = render_template_string(template_str, **context)
    # This is a simplified way to handle the layout since we can't use separate files
    # In a real app, we'd use render_template, but here we manually wrap
    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', content))

# API and Web Routes

@app.route('/entries', methods=['GET'])
def list_entries():
    if request.args.get('format') == 'json':
        with get_db() as conn:
            rows = conn.execute('SELECT id, title FROM entries').fetchall()
            return jsonify([dict(row) for row in rows])
    
    with get_db() as conn:
        rows = conn.execute('SELECT id, title FROM entries').fetchall()
        return render_with_layout(INDEX_TPL, entries=rows)

@app.route('/')
def home():
    return redirect(url_for('list_entries'))

@app.route('/entries', methods=['POST'])
def create_entry():
    data = request.json if request.is_json else request.form
    title = data.get('title')
    content = data.get('content')
    user = data.get('createdBy')

    if not all([title, content, user]):
        return jsonify({"error": "Missing required fields"}), 400

    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute('INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)',
                     (entry_id, title, content, user, now))
        conn.execute('INSERT INTO edits (entry_id, contributor, content_snapshot, summary, timestamp) VALUES (?, ?, ?, ?, ?)',
                     (entry_id, user, content, "Initial creation", now))
        conn.commit()

    return jsonify({"id": entry_id, "title": title, "content": content, "lastModifiedBy": user, "lastModifiedAt": now}), 201

@app.route('/create', methods=['GET', 'POST'])
def create_page():
    if request.method == 'POST':
        # We simulate the API call logic here for the web form
        title = request.form.get('title')
        content = request.form.get('content')
        user = request.form.get('createdBy')
        
        entry_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with get_db() as conn:
            conn.execute('INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)',
                         (entry_id, title, content, user, now))
            conn.execute('INSERT INTO edits (entry_id, contributor, content_snapshot, summary, timestamp) VALUES (?, ?, ?, ?, ?)',
                         (entry_id, user, content, "Initial creation", now))
            conn.commit()
        return redirect(url_for('get_entry', entryId=entry_id))
    
    return render_with_layout(CREATE_TPL)

@app.route('/entries/<entryId>', methods=['GET'])
def get_entry(entryId):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
        if not row:
            abort(404)
        
        entry = {
            "id": row['id'],
            "title": row['title'],
            "content": row['content'],
            "lastModifiedBy": row['last_modified_by'],
            "lastModifiedAt": row['last_modified_at']
        }
        
    if request.args.get('format') == 'json':
        return jsonify(entry)
        
    return render_with_layout(ENTRY_TPL, entry=entry)

@app.route('/entries/<entryId>', methods=['PUT'])
def update_entry(entryId):
    data = request.json
    content = data.get('content')
    user = data.get('modifiedBy')
    summary = data.get('summary')

    if not all([content, user, summary]):
        return jsonify({"error": "Missing required fields"}), 400

    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        row = conn.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
        if not row:
            abort(404)
        
        conn.execute('UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?',
                     (content, user, now, entryId))
        conn.execute('INSERT INTO edits (entry_id, contributor, content_snapshot, summary, timestamp) VALUES (?, ?, ?, ?, ?)',
                     (entryId, user, content, summary, now))
        conn.commit()

    return jsonify({"id": entryId, "content": content, "lastModifiedBy": user, "lastModifiedAt": now}), 200

@app.route('/entries/<entryId>/edit', methods=['GET', 'POST'])
def edit_page(entryId):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
        if not row:
            abort(404)
        
        entry = {"id": row['id'], "title": row['title'], "content": row['content'], "lastModifiedBy": row['last_modified_by']}

    if request.method == 'POST':
        content = request.form.get('content')
        user = request.form.get('modifiedBy')
        summary = request.form.get('summary')
        now = datetime.utcnow().isoformat()
        
        with get_db() as conn:
            conn.execute('UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?',
                         (content, user, now, entryId))
            conn.execute('INSERT INTO edits (entry_id, contributor, content_snapshot, summary, timestamp) VALUES (?, ?, ?, ?, ?)',
                         (entryId, user, content, summary, now))
            conn.commit()
        return redirect(url_for('get_entry', entryId=entryId))

    return render_with_layout(EDIT_TPL, entry=entry)

@app.route('/entries/<entryId>/edits', methods=['GET'])
def get_history(entryId):
    with get_db() as conn:
        row = conn.execute('SELECT title FROM entries WHERE id = ?', (entryId,)).fetchone()
        if not row:
            abort(404)
        
        edits = conn.execute('SELECT contributor, content_snapshot as content, summary, timestamp FROM edits WHERE entry_id = ? ORDER BY timestamp DESC', (entryId,)).fetchall()
        
    return render_with_layout(HISTORY_TPL, title=row['title'], edits=edits)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)