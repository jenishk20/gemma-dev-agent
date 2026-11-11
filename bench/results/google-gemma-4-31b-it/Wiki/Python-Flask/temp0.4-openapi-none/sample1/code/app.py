import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, abort, redirect, url_for

app = Flask(__name__)

DB_NAME = "db.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                last_modified_by TEXT,
                last_modified_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER,
                modified_by TEXT,
                content_snapshot TEXT,
                summary TEXT,
                modified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES entries(id)
            )
        ''')
        conn.commit()

# HTML Templates
LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki App</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        .nav { margin-bottom: 20px; }
        .entry-box { border: 1px solid #ccc; padding: 15px; border-radius: 5px; }
        .diff { background: #f9f9f9; border-left: 3px solid #ccc; padding: 10px; margin: 10px 0; white-space: pre-wrap; }
        form div { margin-bottom: 10px; }
        label { display: block; font-weight: bold; }
        input, textarea { width: 100%; padding: 8px; box-sizing: border-box; }
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
{% extends "layout" %}
{% block content %}
    <h1>Wiki Entries</h1>
    <ul>
        {% for entry in entries %}
        <li><a href="/entries/{{ entry.id }}">{{ entry.title }}</a></li>
        {% endfor %}
    </ul>
    <hr>
    <h3>Create New Entry</h3>
    <form action="/entries" method="post">
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
        <button type="submit">Create Entry</button>
    </form>
{% endblock %}
"""

ENTRY_TEMPLATE = """
{% extends "layout" %}
{% block content %}
    <h1>{{ entry.title }}</h1>
    <div class="entry-box">
        <p>{{ entry.content }}</p>
    </div>
    <div class="meta">
        Last modified by {{ entry.lastModifiedBy }} on {{ entry.lastModifiedAt }}
    </div>
    <p><a href="/entries/{{ entry.id }}/edits">View History</a></p>
    <hr>
    <h3>Edit Entry</h3>
    <form action="/entries/{{ entry.id }}" method="post">
        <input type="hidden" name="_method" value="PUT">
        <div>
            <label>Content</label>
            <textarea name="content" required>{{ entry.content }}</textarea>
        </div>
        <div>
            <label>Your Name</label>
            <input type="text" name="modifiedBy" required>
        </div>
        <div>
            <label>Edit Summary</label>
            <input type="text" name="summary" required>
        </div>
        <button type="submit">Save Changes</button>
    </form>
{% endblock %}
"""

HISTORY_TEMPLATE = """
{% extends "layout" %}
{% block content %}
    <h1>History for {{ title }}</h1>
    {% for edit in edits %}
        <div class="entry-box" style="margin-bottom: 20px;">
            <strong>Editor:</strong> {{ edit.modified_by }} | <strong>Date:</strong> {{ edit.modified_at }}<br>
            <strong>Summary:</strong> {{ edit.summary }}
            <div class="diff">
                {{ edit.content_snapshot }}
            </div>
        </div>
    {% endfor %}
{% endblock %}
"""

@app.context_processor
def inject_layout():
    return dict(layout=LAYOUT)

@app.route('/')
def home():
    return redirect(url_for('list_entries'))

@app.route('/entries', methods=['GET'])
def list_entries():
    db = get_db()
    entries = db.execute('SELECT id, title FROM entries').fetchall()
    # We use render_template_string because we are in one file
    return render_template_string(INDEX_TEMPLATE, entries=entries)

@app.route('/entries', methods=['POST'])
def create_entry():
    # Support both JSON and Form data for flexibility
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    title = data.get('title')
    content = data.get('content')
    created_by = data.get('createdBy')

    if not all([title, content, created_by]):
        return jsonify({"error": "Missing required fields"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO entries (title, content, last_modified_by) VALUES (?, ?, ?)', 
                   (title, content, created_by))
    entry_id = cursor.lastrowid
    
    # Initial edit record
    cursor.execute('INSERT INTO edits (entry_id, modified_by, content_snapshot, summary) VALUES (?, ?, ?, ?)', 
                   (entry_id, created_by, content, "Initial creation"))
    db.commit()

    return jsonify({
        "id": str(entry_id),
        "title": title,
        "content": content,
        "lastModifiedBy": created_by,
        "lastModifiedAt": datetime.now().isoformat()
    }), 201

@app.route('/entries/<int:entryId>', methods=['GET'])
def get_entry(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    
    entry_data = {
        "id": str(entry['id']),
        "title": entry['title'],
        "content": entry['content'],
        "lastModifiedBy": entry['last_modified_by'],
        "lastModifiedAt": entry['last_modified_at']
    }
    
    # If request is for HTML (browser), render template
    if "text/html" in request.headers.get('Accept', 'text/html'):
        return render_template_string(ENTRY_TEMPLATE, entry=entry_data)
    
    return jsonify(entry_data)

@app.route('/entries/<int:entryId>', methods=['POST', 'PUT'])
def update_entry(entryId):
    # Handle HTML form simulating PUT via _method hidden field
    if request.method == 'POST' and request.form.get('_method') == 'PUT':
        method = 'PUT'
    else:
        method = request.method

    if method != 'PUT':
        return jsonify({"error": "Method not allowed"}), 405

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

    now = datetime.now().isoformat()
    db.execute('UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?', 
               (content, modified_by, now, entryId))
    db.execute('INSERT INTO edits (entry_id, modified_by, content_snapshot, summary) VALUES (?, ?, ?, ?)', 
               (entryId, modified_by, content, summary))
    db.commit()

    return jsonify({
        "id": str(entryId),
        "content": content,
        "lastModifiedBy": modified_by,
        "lastModifiedAt": now
    })

@app.route('/entries/<int:entryId>/edits', methods=['GET'])
def get_history(entryId):
    db = get_db()
    entry = db.execute('SELECT title FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    
    edits = db.execute('SELECT * FROM edits WHERE entry_id = ? ORDER BY modified_at DESC', (entryId,)).fetchall()
    
    return render_template_string(HISTORY_TEMPLATE, title=entry['title'], edits=edits)

# Custom template rendering to handle the layout wrap
@app.before_request
def setup_templates():
    # This is a hack to make render_template_string work with a base layout
    # since we can't use separate files.
    def render_with_layout(template_str, **kwargs):
        content = render_template_string(template_str, **kwargs)
        return render_template_string(LAYOUT, content=content)
    
    # We override the internal render_template_string behavior for our specific templates
    # by wrapping the logic inside the routes instead.
    pass

# Overriding the routes to actually use the layout
def wrap_html(template_name, **kwargs):
    if template_name == INDEX_TEMPLATE:
        t = INDEX_TEMPLATE
    elif template_name == ENTRY_TEMPLATE:
        t = ENTRY_TEMPLATE
    elif template_name == HISTORY_TEMPLATE:
        t = HISTORY_TEMPLATE
    else:
        t = template_name
    
    # Render the inner content
    inner_html = render_template_string(t, **kwargs)
    # Render the layout and inject the inner html into the 'content' block
    return render_template_string(LAYOUT, content=inner_html)

# Redefining routes to use the wrapper
@app.route('/entries', methods=['GET'])
def list_entries_wrapped():
    db = get_db()
    entries = db.execute('SELECT id, title FROM entries').fetchall()
    return wrap_html(INDEX_TEMPLATE, entries=entries)

@app.route('/entries/<int:entryId>', methods=['GET'])
def get_entry_wrapped(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry: abort(404)
    entry_data = {"id": str(entry['id']), "title": entry['title'], "content": entry['content'], 
                  "lastModifiedBy": entry['last_modified_by'], "lastModifiedAt": entry['last_modified_at']}
    if "text/html" in request.headers.get('Accept', 'text/html'):
        return wrap_html(ENTRY_TEMPLATE, entry=entry_data)
    return jsonify(entry_data)

@app.route('/entries/<int:entryId>/edits', methods=['GET'])
def get_history_wrapped(entryId):
    db = get_db()
    entry = db.execute('SELECT title FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry: abort(404)
    edits = db.execute('SELECT * FROM edits WHERE entry_id = ? ORDER BY modified_at DESC', (entryId,)).fetchall()
    return wrap_html(HISTORY_TEMPLATE, title=entry['title'], edits=edits)

# Since we redefined the routes, we need to clear the old ones or just use the new ones.
# To keep it simple, I'll just use the wrapped versions.
app.route('/entries', methods=['GET'])(list_entries_wrapped)
app.route('/entries/<int:entryId>', methods=['GET'])(get_entry_wrapped)
app.route('/entries/<int:entryId>/edits', methods=['GET'])(get_history_wrapped)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)