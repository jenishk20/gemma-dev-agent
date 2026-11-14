import sqlite3
import uuid
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, abort, jsonify

app = Flask(__name__)

# Database initialization
DB_NAME = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Entries table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                lastModifiedBy TEXT,
                lastModifiedAt TEXT
            )
        ''')
        # Edits table for history tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entryId TEXT NOT NULL,
                content TEXT,
                modifiedBy TEXT,
                summary TEXT,
                modifiedAt TEXT,
                FOREIGN KEY (entryId) REFERENCES entries (id)
            )
        ''')
        conn.commit()

# HTML Templates
LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki WebApp</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-box { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .history-item { border-bottom: 1px solid #eee; padding: 10px 0; }
        .diff-added { background-color: #e6ffed; color: #22863a; }
        .diff-removed { background-color: #ffeef0; color: #cb247b; }
        textarea { width: 100%; height: 200px; }
        input[type="text"] { width: 100%; padding: 8px; margin-bottom: 10px; }
        .btn { padding: 10px 15px; background: #007bff; color: white; border: none; cursor: pointer; text-decoration: none; }
    </style>
</head>
<body>
    <nav>
        <strong><a href="{{ url_for('index') }}">Wiki Home</a></strong> | 
        <a href="{{ url_for('create_page') }}">Create New Entry</a>
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
        <li><a href="{{ url_for('get_entry', entryId=entry.id) }}">{{ entry.title }}</a></li>
    {% endfor %}
    </ul>
{% endblock %}
"""

ENTRY_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>{{ entry.title }}</h1>
    <p><em>Last modified by {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}</em></p>
    <div class="entry-box">
        {{ entry.content | safe }}
    </div>
    <p>
        <a class="btn" href="{{ url_for('edit_entry', entryId=entry.id) }}">Edit this page</a>
        <a href="{{ url_for('get_history', entryId=entry.id) }}">View History</a>
    </p>
{% endblock %}
"""

CREATE_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>Create New Entry</h1>
    <form method="POST" action="{{ url_for('create_entry') }}">
        <label>Title:</label><br>
        <input type="text" name="title" required><br>
        <label>Content:</label><br>
        <textarea name="content" required></textarea><br>
        <label>Your Name:</label><br>
        <input type="text" name="createdBy" required><br>
        <button type="submit" class="btn">Save Entry</button>
    </form>
{% endblock %}
"""

EDIT_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>Editing: {{ entry.title }}</h1>
    <form method="POST" action="{{ url_for('update_entry', entryId=entry.id) }}">
        <label>Content:</label><br>
        <textarea name="content" required>{{ entry.content }}</textarea><br>
        <label>Your Name:</label><br>
        <input type="text" name="modifiedBy" required><br>
        <label>Edit Summary:</label><br>
        <input type="text" name="summary" required placeholder="What did you change?"><br>
        <button type="submit" class="btn">Save Changes</button>
    </form>
{% endblock %}
"""

HISTORY_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>History for {{ title }}</h1>
    {% for edit in edits %}
        <div class="history-item">
            <strong>{{ edit.modifiedBy }}</strong> - {{ edit.modifiedAt }}<br>
            <em>Summary: {{ edit.summary }}</em><br>
            <pre style="white-space: pre-wrap;">{{ edit.diff }}</pre>
        </div>
    {% endfor %}
{% endblock %}
"""

# Helper to render templates with the layout
def render_wiki(template_str, **context):
    return render_template_string(template_str, **context)

# Simple diff implementation for history
def generate_diff(old_text, new_text):
    if old_text == new_text:
        return "No changes made to content."
    # Very basic line-by-line diff for demonstration
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff = []
    # This is a naive diff; in production, use difflib
    import difflib
    diff_gen = difflib.ndiff(old_lines, new_lines)
    for line in diff_gen:
        if line.startswith('+ '):
            diff.append(f"+ {line[2:]}")
        elif line.startswith('- '):
            diff.append(f"- {line[2:]}")
    return "\n".join(diff) if diff else "Minor changes."

# --- Routes ---

@app.route('/')
def index():
    conn = get_db_connection()
    entries = conn.execute('SELECT id, title FROM entries').fetchall()
    conn.close()
    # The OpenAPI says /entries GET returns text/html
    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', render_template_string(INDEX_TPL, entries=entries)))

@app.route('/create', methods=['GET'])
def create_page():
    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', render_template_string(CREATE_TPL)))

@app.route('/entries', methods=['POST'])
def create_entry():
    # Handle both JSON (API) and Form (Web)
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    title = data.get('title')
    content = data.get('content')
    created_by = data.get('createdBy')

    if not all([title, content, created_by]):
        return jsonify({"error": "Missing required fields"}), 400

    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = get_db_connection()
    conn.execute('INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)',
                 (entry_id, title, content, created_by, now))
    conn.execute('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)',
                 (entry_id, content, created_by, "Initial creation", now))
    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify({"id": entry_id, "title": title, "content": content, "lastModifiedBy": created_by, "lastModifiedAt": now}), 201
    return redirect(url_for('index'))

@app.route('/entries/<entryId>', methods=['GET'])
def get_entry(entryId):
    conn = get_db_connection()
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    conn.close()

    if entry is None:
        abort(404)

    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', render_template_string(ENTRY_TPL, entry=entry)))

@app.route('/edit/<entryId>', methods=['GET'])
def edit_page(entryId):
    conn = get_db_connection()
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    conn.close()
    if entry is None:
        abort(404)
    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', render_template_string(EDIT_TPL, entry=entry)))

@app.route('/entries/<entryId>', methods=['PUT', 'POST'])
def update_entry(entryId):
    # Support POST for web forms and PUT for API
    if request.method == 'PUT' or request.is_json:
        data = request.get_json() if request.is_json else request.form
    else:
        data = request.form

    content = data.get('content')
    modified_by = data.get('modifiedBy')
    summary = data.get('summary')

    if not all([content, modified_by, summary]):
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    entry = conn.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    
    if entry is None:
        conn.close()
        abort(404)

    now = datetime.utcnow().isoformat()
    conn.execute('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?',
                 (content, modified_by, now, entryId))
    conn.execute('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)',
                 (entryId, content, modified_by, summary, now))
    conn.commit()
    
    updated_entry = conn.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    conn.close()

    if request.is_json or request.method == 'PUT':
        return jsonify({
            "id": updated_entry['id'],
            "title": updated_entry['title'],
            "content": updated_entry['content'],
            "lastModifiedBy": updated_entry['lastModifiedBy'],
            "lastModifiedAt": updated_entry['lastModifiedAt']
        })
    return redirect(url_for('get_entry', entryId=entryId))

@app.route('/entries/<entryId>/edits', methods=['GET'])
def get_history(entryId):
    conn = get_db_connection()
    entry = conn.execute('SELECT title FROM entries WHERE id = ?', (entryId,)).fetchone()
    if entry is None:
        conn.close()
        abort(404)
    
    # Get all edits ordered by date
    edits_rows = conn.execute('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', (entryId,)).fetchall()
    conn.close()

    # Process diffs
    history = []
    # To calculate diffs, we need the previous version
    # We iterate through the edits in ascending order to build diffs, then reverse for display
    sorted_edits = sorted(edits_rows, key=lambda x: x['modifiedAt'])
    prev_content = ""
    
    for row in sorted_edits:
        diff = generate_diff(prev_content, row['content'])
        history.append({
            'modifiedBy': row['modifiedBy'],
            'modifiedAt': row['modifiedAt'],
            'summary': row['summary'],
            'diff': diff
        })
        prev_content = row['content']

    # Reverse back to descending order
    history.reverse()

    return render_template_string(LAYOUT.replace('{% block content %}{% endblock %}', render_template_string(HISTORY_TPL, title=entry['title'], edits=history)))

# Custom template handling to allow the layout to work with render_template_string
@app.context_processor
def inject_layout():
    return dict(layout=LAYOUT)

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)