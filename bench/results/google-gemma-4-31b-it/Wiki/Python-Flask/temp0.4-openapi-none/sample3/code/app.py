import sqlite3
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, url_for

app = Flask(__name__)
DATABASE = 'db.sqlite3'

# --- Database Setup ---
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Entries table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                lastModifiedBy TEXT,
                lastModifiedAt TEXT
            )
        ''')
        # Edits table for change tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entryId TEXT,
                content TEXT,
                modifiedBy TEXT,
                summary TEXT,
                timestamp TEXT,
                FOREIGN KEY(entryId) REFERENCES entries(id)
            )
        ''')
        conn.commit()

init_db()

# --- HTML Templates ---
LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki App</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-box { border: 1px solid #ddd; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
        .diff { background: #f4f4f4; padding: 10px; border-left: 3px solid #ccc; white-space: pre-wrap; font-family: monospace; }
        form { display: flex; flex-direction: column; gap: 10px; max-width: 500px; }
        input, textarea { padding: 8px; }
        textarea { height: 200px; }
    </style>
</head>
<body>
    <nav><a href="/">🏠 Home</a> | <a href="/create">➕ New Entry</a></nav>
    {% block content %}{% endblock %}
</body>
</html>
"""

INDEX_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>Wiki Entries</h1>
    {% for entry in entries %}
        <div class="entry-box">
            <h3><a href="/entries/{{ entry.id }}">{{ entry.title }}</a></h3>
            <p>Last edited by {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}</p>
        </div>
    {% endfor %}
{% endblock %}
"""

ENTRY_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>{{ entry.title }}</h1>
    <p><strong>Last Modified:</strong> {{ entry.lastModifiedAt }} by {{ entry.lastModifiedBy }}</p>
    <div style="white-space: pre-wrap; border: 1px solid #eee; padding: 15px; background: #fafafa;">{{ entry.content }}</div>
    <hr>
    <p><a href="/entries/{{ entry.id }}/edit">✏️ Edit this page</a> | <a href="/entries/{{ entry.id }}/edits">📜 View History</a></p>
{% endblock %}
"""

EDIT_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>Edit: {{ entry.title }}</h1>
    <form method="POST" action="/entries/{{ entry.id }}">
        <label>Your Name:</label>
        <input type="text" name="modifiedBy" required value="{{ entry.lastModifiedBy }}">
        <label>Edit Summary:</label>
        <input type="text" name="summary" required placeholder="What did you change?">
        <label>Content:</label>
        <textarea name="content" required>{{ entry.content }}</textarea>
        <button type="submit">Save Changes</button>
    </form>
{% endblock %}
"""

CREATE_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>Create New Entry</h1>
    <form method="POST" action="/entries">
        <label>Title:</label>
        <input type="text" name="title" required>
        <label>Your Name:</label>
        <input type="text" name="createdBy" required>
        <label>Content:</label>
        <textarea name="content" required></textarea>
        <button type="submit">Create Entry</button>
    </form>
{% endblock %}
"""

HISTORY_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>Edit History: {{ title }}</h1>
    {% for edit in edits %}
        <div class="entry-box">
            <strong>{{ edit.modifiedBy }}</strong> - {{ edit.timestamp }}<br>
            <em>Summary: {{ edit.summary }}</em>
            <div class="diff">{{ edit.content }}</div>
        </div>
    {% endfor %}
{% endblock %}
"""

# --- Routes ---

@app.route('/')
def index():
    # The OpenAPI spec says /entries GET returns text/html
    # We'll use the same route for the home page for convenience
    return redirect(url_for('list_entries'))

@app.route('/entries', methods=['GET'])
def list_entries():
    db = get_db()
    entries = db.execute('SELECT * FROM entries').fetchall()
    return render_template_string(INDEX_TPL, entries=entries, layout=LAYOUT)

@app.route('/create')
def create_page():
    return render_template_string(CREATE_TPL, layout=LAYOUT)

@app.route('/entries', methods=['POST'])
def create_entry():
    # Handle both JSON (API) and Form (Web)
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
    
    db = get_db()
    db.execute('INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)',
               (entry_id, title, content, user, now))
    db.execute('INSERT INTO edits (entryId, content, modifiedBy, summary, timestamp) VALUES (?, ?, ?, ?, ?)',
               (entry_id, content, user, "Initial creation", now))
    db.commit()

    if request.is_json:
        return jsonify({"id": entry_id, "title": title, "content": content, "lastModifiedBy": user, "lastModifiedAt": now}), 201
    return redirect(url_for('list_entries'))

@app.route('/entries/<entryId>', methods=['GET'])
def get_entry(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        return "Entry not found", 404
    return render_template_string(ENTRY_TPL, entry=entry, layout=LAYOUT)

@app.route('/entries/<entryId>/edit', methods=['GET'])
def edit_page(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        return "Entry not found", 404
    return render_template_string(EDIT_TPL, entry=entry, layout=LAYOUT)

@app.route('/entries/<entryId>', methods=['PUT', 'POST'])
def update_entry(entryId):
    # Support POST for the HTML form, PUT for the API
    if request.method == 'PUT':
        if not request.is_json: return "Expected JSON", 400
        data = request.get_json()
    else:
        data = request.form

    content = data.get('content')
    user = data.get('modifiedBy')
    summary = data.get('summary')

    if not all([content, user, summary]):
        return jsonify({"error": "Missing required fields"}), 400

    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        return jsonify({"error": "Not found"}), 404

    now = datetime.now().isoformat()
    db.execute('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?',
               (content, user, now, entryId))
    db.execute('INSERT INTO edits (entryId, content, modifiedBy, summary, timestamp) VALUES (?, ?, ?, ?, ?)',
               (entryId, content, user, summary, now))
    db.commit()

    if request.method == 'PUT':
        return jsonify({"id": entryId, "title": entry['title'], "content": content, "lastModifiedBy": user, "lastModifiedAt": now})
    return redirect(url_for('get_entry', entryId=entryId))

@app.route('/entries/<entryId>/edits', methods=['GET'])
def view_history(entryId):
    db = get_db()
    entry = db.execute('SELECT title FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        return "Entry not found", 404
    
    edits = db.execute('SELECT * FROM edits WHERE entryId = ? ORDER BY timestamp DESC', (entryId,)).fetchall()
    return render_template_string(HISTORY_TPL, title=entry['title'], edits=edits, layout=LAYOUT)

# Context processor to make LAYOUT available to all templates
@app.context_processor
def inject_layout():
    return dict(layout=LAYOUT)

if __name__ == '__main__':
    # Overriding the default layout variable in templates requires a bit of a trick 
    # since we are using render_template_string. 
    # We'll just pass it explicitly or use a custom base.
    # To ensure the layout is used, we wrap the content.
    
    # Patching render_template_string to handle the 'layout' variable for the base template
    original_render = app.jinja_env.get_template
    def wrapped_render(template_name, **kwargs):
        # This is a simplification for the single-file requirement
        return original_render(template_name, **kwargs)
    
    # Since we are using render_template_string, we just pass the layout string 
    # and use {% extends "layout" %}. 
    # To make "layout" a valid template name, we add it to the jinja environment.
    from jinja2 import DictLoader
    app.jinja_env.loader = DictLoader({'layout': LAYOUT})

    app.run(host='0.0.0.0', port=5000, debug=False)