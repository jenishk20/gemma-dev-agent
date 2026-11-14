import sqlite3
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, abort

app = Flask(__name__)
app.config['DATABASE'] = 'db.sqlite3'

# HTML Templates
BASE_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki WebApp</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; max-width: 800px; margin: auto; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-box { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .meta { color: #666; font-size: 0.9em; }
        .diff { background: #f9f9f9; padding: 10px; border-left: 3px solid #ccc; white-space: pre-wrap; }
        form { display: flex; flex-direction: column; gap: 10px; max-width: 400px; }
        input, textarea { padding: 8px; width: 100%; }
        button { cursor: pointer; padding: 10px; background: #007BFF; color: white; border: none; border-radius: 3px; }
    </style>
</head>
<body>
    <nav><a href="/">🏠 Home</a> | <a href="/create">➕ New Entry</a></nav>
    {% block content %}{% endblock %}
</body>
</html>
"""

INDEX_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>Wiki Entries</h1>
    <ul>
        {% for entry in entries %}
            <li><a href="/entries/{{ entry[0] }}">{{ entry[1] }}</a></li>
        {% endfor %}
    </ul>
{% endblock %}
"""

ENTRY_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>{{ entry.title }}</h1>
    <div class="entry-box">
        <p>{{ entry.content }}</p>
    </div>
    <div class="meta">
        <p>Last modified by: {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}</p>
    </div>
    <p>
        <a href="/entries/{{ entry.id }}/edit">Edit this page</a> | 
        <a href="/entries/{{ entry.id }}/edits">View History</a>
    </p>
{% endblock %}
"""

EDIT_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>Edit Entry</h1>
    <form method="POST" action="/entries/{{ entry_id }}">
        <label>Content:</label>
        <textarea name="content" rows="10" required>{{ current_content }}</textarea>
        <label>Your Name:</label>
        <input type="text" name="modifiedBy" required>
        <label>Edit Summary:</label>
        <input type="text" name="summary" required>
        <button type="submit">Save Changes</button>
    </form>
{% endblock %}
"""

HISTORY_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>Edit History: {{ title }}</h1>
    {% for edit in edits %}
        <div class="entry-box" style="margin-bottom: 20px;">
            <p><strong>{{ edit.user }}</strong> - {{ edit.date }}</p>
            <p><em>Summary: {{ edit.summary }}</em></p>
            <div class="diff">{{ edit.content }}</div>
        </div>
    {% endfor %}
{% endblock %}
"""

CREATE_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>Create New Entry</h1>
    <form method="POST" action="/entries">
        <label>Title:</label>
        <input type="text" name="title" required>
        <label>Content:</label>
        <textarea name="content" rows="10" required></textarea>
        <label>Your Name:</label>
        <input type="text" name="createdBy" required>
        <button type="submit">Create Entry</button>
    </form>
{% endblock %}
"""

def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS entries (id TEXT PRIMARY KEY, title TEXT, content TEXT, lastModifiedBy TEXT, lastModifiedAt TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS edits (id INTEGER PRIMARY KEY AUTOINCREMENT, entryId TEXT, content TEXT, modifiedBy TEXT, summary TEXT, modifiedAt TEXT)')
        conn.commit()

@app.context_processor
def inject_base():
    return {'base': BASE_LAYOUT}

@app.route('/')
def index():
    conn = get_db()
    entries = conn.execute('SELECT id, title FROM entries').fetchall()
    return render_template_string(INDEX_TEMPLATE, entries=entries)

@app.route('/create', methods=['GET'])
def create_page():
    return render_template_string(CREATE_TEMPLATE)

@app.route('/entries', methods=['POST'])
def create_entry():
    # Support both JSON (API) and Form (Web)
    if request.is_json:
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')
        user = data.get('createdBy')
    else:
        title = request.form.get('title')
        content = request.form.get('content')
        user = request.form.get('createdBy')

    if not all([title, content, user]):
        return jsonify({"error": "Missing required fields"}), 400

    entry_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    conn = get_db()
    conn.execute('INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)', 
                 (entry_id, title, content, user, now))
    conn.execute('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
                 (entry_id, content, user, "Initial creation", now))
    conn.commit()

    if request.is_json:
        return jsonify({"id": entry_id, "title": title, "content": content, "lastModifiedBy": user, "lastModifiedAt": now}), 201
    return redirect(url_for('index'))

@app.route('/entries/<entryId>', methods=['GET'])
def get_entry(entryId):
    conn = get_db()
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    
    if request.accept_mimetypes == 'application/json':
        return jsonify(dict(entry))
    
    return render_template_string(ENTRY_TEMPLATE, entry=entry)

@app.route('/entries/<entryId>', methods=['PUT', 'POST'])
def update_entry(entryId):
    # PUT for API, POST for Web Form
    if request.method == 'PUT':
        data = request.get_json()
        content = data.get('content')
        user = data.get('modifiedBy')
        summary = data.get('summary')
    else:
        content = request.form.get('content')
        user = request.form.get('modifiedBy')
        summary = request.form.get('summary')

    if not all([content, user, summary]):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db()
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)

    now = datetime.now().isoformat()
    conn.execute('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?', 
                 (content, user, now, entryId))
    conn.execute('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
                 (entryId, content, user, summary, now))
    conn.commit()

    if request.method == 'PUT':
        return jsonify({"id": entryId, "content": content, "lastModifiedBy": user, "lastModifiedAt": now}), 200
    return redirect(url_for('get_entry', entryId=entryId))

@app.route('/entries/<entryId>/edit', methods=['GET'])
def edit_page(entryId):
    conn = get_db()
    entry = conn.execute('SELECT content FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    return render_template_string(EDIT_TEMPLATE, entry_id=entryId, current_content=entry['content'])

@app.route('/entries/<entryId>/edits', methods=['GET'])
def get_history(entryId):
    conn = get_db()
    entry = conn.execute('SELECT title FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    
    edits = conn.execute('SELECT content, modifiedBy, summary, modifiedAt FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', (entryId,)).fetchall()
    
    # Convert rows to list of dicts for template
    history = [{"content": e[0], "user": e[1], "summary": e[2], "date": e[3]} for e in edits]
    
    return render_template_string(HISTORY_TEMPLATE, title=entry['title'], edits=history)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)