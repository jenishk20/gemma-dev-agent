import sqlite3
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, jsonify, abort

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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                last_modified_by TEXT,
                last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Edits history table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                contributor TEXT NOT NULL,
                content_snapshot TEXT NOT NULL,
                summary TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES entries (id)
            )
        ''')
        conn.commit()

# --- HTML Templates ---
LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Wiki App</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-box { border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .meta { font-size: 0.8em; color: #666; }
        .diff-add { background-color: #e6ffed; color: #22863a; }
        .diff-del { background-color: #ffeef0; color: #cb2431; }
        textarea { width: 100%; height: 200px; }
        input[type="text"] { width: 100%; padding: 8px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <nav>
        <strong><a href="/">🏠 Home</a></strong> | 
        <a href="/create">➕ New Entry</a>
    </nav>
    {% block content %}{{ content }}{% endblock %}
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
<h1>{{ entry.title }}</h1>
<div class="meta">
    Last modified by {{ entry.last_modified_by }} on {{ entry.last_modified_at }}
</div>
<hr>
<div class="content">{{ entry.content }}</div>
<hr>
<p>
    <a href="/entries/{{ entry.id }}/edit">✏️ Edit this page</a> | 
    <a href="/entries/{{ entry.id }}/edits">📜 History</a>
</p>
{% endblock %}
"""

EDIT_TPL = """
{% extends "layout" %}
{% block content %}
<h1>Edit Entry</h1>
<form method="POST">
    <label>Your Name:</label><br>
    <input type="text" name="modifiedBy" required><br>
    <label>Edit Summary:</label><br>
    <input type="text" name="summary" required><br>
    <label>Content:</label><br>
    <textarea name="content" required>{{ entry.content }}</textarea><br>
    <button type="submit">Save Changes</button>
</form>
{% endblock %}
"""

CREATE_TPL = """
{% extends "layout" %}
{% block content %}
<h1>Create New Entry</h1>
<form method="POST">
    <label>Title:</label><br>
    <input type="text" name="title" required><br>
    <label>Your Name:</label><br>
    <input type="text" name="createdBy" required><br>
    <label>Content:</label><br>
    <textarea name="content" required></textarea><br>
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
    <div class="meta">
        <strong>{{ edit.contributor }}</strong> - {{ edit.timestamp }}<br>
        <em>{{ edit.summary }}</em>
    </div>
    <pre style="white-space: pre-wrap;">{{ edit.diff }}</pre>
</div>
{% endfor %}
{% endblock %}
"""

# --- Helpers ---
def simple_diff(old_text, new_text):
    # A very basic line-by-line diff for visualization
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    result = []
    # This is a naive diff; in a real app we'd use difflib
    import difflib
    diff = difflib.ndiff(old_lines, new_lines)
    for line in diff:
        if line.startswith('+ '):
            result.append(f"<span class='diff-add'>+ {line[2:]}</span>")
        elif line.startswith('- '):
            result.append(f"<span class='diff-del'>- {line[2:]}</span>")
        elif line.startswith('  '):
            result.append(f"  {line[2:]}")
    return "<br>".join(result)

# --- Routes ---

@app.route('/layout')
def layout():
    return LAYOUT

@app.route('/')
def index():
    db = get_db()
    entries = db.execute('SELECT id, title FROM entries').fetchall()
    return render_template_string(INDEX_TPL, entries=entries)

@app.route('/create', methods=['GET', 'POST'])
def create_entry_page():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        user = request.form.get('createdBy')
        
        db = get_db()
        cur = db.cursor()
        cur.execute('INSERT INTO entries (title, content, last_modified_by) VALUES (?, ?, ?)', 
                    (title, content, user))
        entry_id = cur.lastrowid
        cur.execute('INSERT INTO edits (entry_id, contributor, content_snapshot, summary) VALUES (?, ?, ?, ?)', 
                    (entry_id, user, content, "Initial creation"))
        db.commit()
        return redirect(url_for('get_entry', entryId=entry_id))
    
    return render_template_string(CREATE_TPL)

@app.route('/entries', methods=['GET', 'POST'])
def entries_api():
    if request.method == 'GET':
        # The OpenAPI schema asks for text/html for GET /entries
        return index()
    
    if request.method == 'POST':
        data = request.json
        if not data or not all(k in data for k in ('title', 'content', 'createdBy')):
            return jsonify({"error": "Missing required fields"}), 400
        
        db = get_db()
        cur = db.cursor()
        cur.execute('INSERT INTO entries (title, content, last_modified_by) VALUES (?, ?, ?)', 
                    (data['title'], data['content'], data['createdBy']))
        entry_id = cur.lastrowid
        cur.execute('INSERT INTO edits (entry_id, contributor, content_snapshot, summary) VALUES (?, ?, ?, ?)', 
                    (entry_id, data['createdBy'], data['content'], "Initial creation"))
        db.commit()
        
        return jsonify({
            "id": str(entry_id),
            "title": data['title'],
            "content": data['content'],
            "lastModifiedBy": data['createdBy'],
            "lastModifiedAt": datetime.now().isoformat()
        }), 201

@app.route('/entries/<entryId>', methods=['GET'])
def get_entry(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    
    # Return HTML as per schema
    return render_template_string(ENTRY_TPL, entry=entry)

@app.route('/entries/<entryId>/edit', methods=['GET', 'POST'])
def edit_entry_page(entryId):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)

    if request.method == 'POST':
        content = request.form.get('content')
        user = request.form.get('modifiedBy')
        summary = request.form.get('summary')
        
        db.execute('UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = CURRENT_TIMESTAMP WHERE id = ?', 
                   (content, user, entryId))
        db.execute('INSERT INTO edits (entry_id, contributor, content_snapshot, summary) VALUES (?, ?, ?, ?)', 
                   (entryId, user, content, summary))
        db.commit()
        return redirect(url_for('get_entry', entryId=entryId))

    return render_template_string(EDIT_TPL, entry=entry)

@app.route('/entries/<entryId>', methods=['PUT'])
def update_entry_api(entryId):
    data = request.json
    if not data or not all(k in data for k in ('content', 'modifiedBy', 'summary')):
        return jsonify({"error": "Missing required fields"}), 400
    
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    
    db.execute('UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = CURRENT_TIMESTAMP WHERE id = ?', 
               (data['content'], data['modifiedBy'], entryId))
    db.execute('INSERT INTO edits (entry_id, contributor, content_snapshot, summary) VALUES (?, ?, ?, ?)', 
               (entryId, data['modifiedBy'], data['content'], data['summary']))
    db.commit()
    
    return jsonify({
        "id": entryId,
        "title": entry['title'],
        "content": data['content'],
        "lastModifiedBy": data['modifiedBy'],
        "lastModifiedAt": datetime.now().isoformat()
    })

@app.route('/entries/<entryId>/edits', methods=['GET'])
def get_edits(entryId):
    db = get_db()
    entry = db.execute('SELECT title FROM entries WHERE id = ?', (entryId,)).fetchone()
    if not entry:
        abort(404)
    
    # Get edits in descending order
    edits_raw = db.execute('SELECT * FROM edits WHERE entry_id = ? ORDER BY timestamp DESC', (entryId,)).fetchall()
    
    # To generate diffs, we need to compare each edit with the one before it (chronologically)
    processed_edits = []
    # Sort ascending to calculate diffs
    chronological_edits = sorted(edits_raw, key=lambda x: x['timestamp'])
    
    prev_content = ""
    for e in chronological_edits:
        diff_html = simple_diff(prev_content, e['content_snapshot'])
        processed_edits.append({
            'contributor': e['contributor'],
            'timestamp': e['timestamp'],
            'summary': e['summary'],
            'diff': diff_html
        })
        prev_content = e['content_snapshot']
    
    # Reverse back to show newest first
    processed_edits.reverse()
    
    return render_template_string(HISTORY_TPL, title=entry['title'], edits=processed_edits)

# --- Template Overrides ---
@app.context_processor
def inject_layout():
    # This allows the templates to use 'layout' as a base
    return dict(layout=LAYOUT)

# Custom template loader to handle the 'layout' extension without a file
from jinja2 import ChoiceLoader, FileSystemLoader, DictLoader
app.jinja_env.loader = ChoiceLoader([
    DictLoader({'layout': LAYOUT}),
    FileSystemLoader('.')
])

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)