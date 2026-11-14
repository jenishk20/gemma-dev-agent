import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, abort

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
                last_modified_by TEXT,
                last_modified_at TEXT
            )
        ''')
        # Edits table for change tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT,
                content TEXT,
                modified_by TEXT,
                summary TEXT,
                modified_at TEXT,
                FOREIGN KEY(entry_id) REFERENCES entries(id)
            )
        ''')
        conn.commit()

# --- HTML Templates (In-line for single-file requirement) ---
BASE_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki App</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        .nav { margin-bottom: 20px; }
        .entry-box { border: 1px solid #ccc; padding: 20px; border-radius: 5px; }
        .diff { background: #f4f4f4; padding: 10px; border-left: 3px solid #ddd; white-space: pre-wrap; }
        form { display: flex; flex-direction: column; gap: 10px; max-width: 500px; }
        textarea { height: 200px; }
        .meta { font-size: 0.8em; color: #666; }
    </style>
</head>
<body>
    <div class="nav"><a href="/">🏠 Home</a></div>
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
            <li><a href="{{ url_for('get_entry', entryId=entry['id']) }}">{{ entry['title'] }}</a></li>
        {% endfor %}
    </ul>
    <hr>
    <h2>Create New Entry</h2>
    <form action="/entries" method="post">
        <input type="text" name="title" placeholder="Title" required>
        <textarea name="content" placeholder="Content" required></textarea>
        <input type="text" name="createdBy" placeholder="Your Name" required>
        <button type="submit">Create Entry</button>
    </form>
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
        Last modified by {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}
    </div>
    <p>
        <a href="{{ url_for('get_edits', entryId=entry.id) }}">View History</a> | 
        <a href="{{ url_for('edit_page', entryId=entry.id) }}">Edit this page</a>
    </p>
{% endblock %}
"""

EDIT_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>Edit {{ entry.title }}</h1>
    <form action="{{ url_for('update_entry', entryId=entry.id) }}" method="post">
        <textarea name="content" required>{{ entry.content }}</textarea>
        <input type="text" name="modifiedBy" placeholder="Your Name" required>
        <input type="text" name="summary" placeholder="Edit Summary (e.g. Fixed typo)" required>
        <button type="submit">Save Changes</button>
    </form>
{% endblock %}
"""

HISTORY_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>History for {{ title }}</h1>
    {% for edit in edits %}
        <div class="entry-box" style="margin-bottom: 20px;">
            <div class="meta">
                <strong>{{ edit.modified_by }}</strong> - {{ edit.modified_at }}<br>
                <em>Summary: {{ edit.summary }}</em>
            </div>
            <div class="diff">{{ edit.content }}</div>
        </div>
    {% endfor %}
{% endblock %}
"""

# --- Routes ---

@app.route('/')
def index():
    # This corresponds to GET /entries returning HTML
    db = get_db()
    entries = db.execute('SELECT id, title FROM entries').fetchall()
    return render_template_string(INDEX_TEMPLATE, entries=entries), 200

@app.route('/entries', methods=['POST'])
def create_entry():
    # OpenAPI requires JSON, but for the webapp we handle both form and json
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
    
    title = data.get('title')
    content = data.get('content')
    created_by = data.get('createdBy')

    if not all([title, content, created_by]):
        return jsonify({"error": "Missing required fields"}), 400

    import uuid
    entry_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()

    db = get_db()
    db.execute('INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)',
               (entry_id, title, content, created_by, now))
    db.execute('INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)',
               (entry_id, content, created_by, "Initial creation", now))
    db.commit()

    return jsonify({
        "id": entry_id,
        "title": title,
        "content": content,
        "lastModifiedBy": created_by,
        "lastModifiedAt": now
    }), 201

@app.route('/entries/<entryId>', methods=['GET'])
def get_entry(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    
    # Map DB columns to Schema
    entry_data = {
        "id": entry['id'],
        "title": entry['title'],
        "content": entry['content'],
        "lastModifiedBy": entry['last_modified_by'],
        "lastModifiedAt": entry['last_modified_at']
    }
    return render_template_string(ENTRY_TEMPLATE, entry=entry_data), 200

@app.route('/entries/<entryId>', methods=['PUT', 'POST']) # POST used for HTML form compatibility
def update_entry(entryId):
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    content = data.get('content')
    modified_by = data.get('modifiedBy')
    summary = data.get('summary')

    if not all([content, modified_by, summary]):
        return jsonify({"error": "Missing required fields"}), 400

    db = get_db()
    entry = db.execute('SELECT id FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)

    now = datetime.utcnow().isoformat()
    db.execute('UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?',
               (content, modified_by, now, entryId))
    db.execute('INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)',
               (entryId, content, modified_by, summary, now))
    db.commit()

    return jsonify({
        "id": entryId,
        "content": content,
        "lastModifiedBy": modified_by,
        "lastModifiedAt": now
    }), 200

@app.route('/entries/<entryId>/edits', methods=['GET'])
def get_edits(entryId):
    db = get_db()
    entry = db.execute('SELECT title FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    
    edits = db.execute('SELECT * FROM edits WHERE entry_id = ? ORDER BY modified_at DESC', (entryId,)).fetchall()
    return render_template_string(HISTORY_TEMPLATE, title=entry['title'], edits=edits), 200

@app.route('/edit/<entryId>')
def edit_page(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    return render_template_string(EDIT_TEMPLATE, entry=entry), 200

# --- Jinja2 Global for Base Layout ---
@app.context_processor
def inject_base():
    return {'base_layout': BASE_LAYOUT}

# Override render_template_string to wrap in base layout
original_render = render_template_string
def wrapped_render(source, **kwargs):
    content = original_render(source, **kwargs)
    return original_render(BASE_LAYOUT, content=content, **kwargs)

# Since we can't easily override the internal render_template_string without monkeypatching, 
# I will instead use a simple helper or just include the base in the template strings.
# For simplicity and reliability in a single file, I'll use the 'extends' logic 
# but I must provide the 'base' template to Jinja.

from flask import render_template
import string

# We use a trick to make 'base' available to render_template_string
class TemplateWrapper:
    def __init__(self, template_str):
        self.template_str = template_str
    def __getitem__(self, key):
        if key == 'base': return BASE_LAYOUT
        return None

# Actually, the easiest way is to just use the template strings as they are 
# and define a custom function to handle the base layout.
def render_wiki(template_name, **context):
    # This is a simplified version of a template engine
    # In a real app, we'd use files. Here we just wrap the content.
    # Since we are using render_template_string with {% extends "base" %}, 
    # we need to provide the base template.
    pass

# Let's redefine the templates to not use 'extends' but just include the HTML 
# to ensure it works perfectly in a single-file Flask setup without a filesystem.

INDEX_HTML = BASE_LAYOUT.replace('{% block content %}{% endblock %}', INDEX_TEMPLATE.replace('{% extends "base" %}', '').replace('{% block content %}', '').replace('{% endblock %}', ''))
ENTRY_HTML = BASE_LAYOUT.replace('{% block content %}{% endblock %}', ENTRY_TEMPLATE.replace('{% extends "base" %}', '').replace('{% block content %}', '').replace('{% endblock %}', ''))
EDIT_HTML = BASE_LAYOUT.replace('{% block content %}{% endblock %}', EDIT_TEMPLATE.replace('{% extends "base" %}', '').replace('{% block content %}', '').replace('{% endblock %}', ''))
HISTORY_HTML = BASE_LAYOUT.replace('{% block content %}{% endblock %}', HISTORY_TEMPLATE.replace('{% extends "base" %}', '').replace('{% block content %}', '').replace('{% endblock %}', ''))

# Update routes to use the full HTML
@app.route('/')
def index_final():
    db = get_db()
    entries = db.execute('SELECT id, title FROM entries').fetchall()
    return render_template_string(INDEX_HTML, entries=entries)

@app.route('/entries/<entryId>', methods=['GET'])
def get_entry_final(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry: abort(404)
    entry_data = {"id": entry['id'], "title": entry['title'], "content": entry['content'], "lastModifiedBy": entry['last_modified_by'], "lastModifiedAt": entry['last_modified_at']}
    return render_template_string(ENTRY_HTML, entry=entry_data)

@app.route('/edit/<entryId>')
def edit_page_final(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry: abort(404)
    return render_template_string(EDIT_HTML, entry=entry)

@app.route('/entries/<entryId>/edits', methods=['GET'])
def get_edits_final(entryId):
    db = get_db()
    entry = db.execute('SELECT title FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry: abort(404)
    edits = db.execute('SELECT * FROM edits WHERE entry_id = ? ORDER BY modified_at DESC', (entryId,)).fetchall()
    return render_template_string(HISTORY_HTML, title=entry['title'], edits=edits)

# Re-mapping the routes to the final versions
app.route('/')(index_final)
app.route('/entries/<entryId>', methods=['GET'])(get_entry_final)
app.route('/edit/<entryId>')(edit_page_final)
app.route('/entries/<entryId>/edits', methods=['GET'])(get_edits_final)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)