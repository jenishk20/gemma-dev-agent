import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, abort, redirect, url_for

app = Flask(__name__)

DB_NAME = "db.sqlite3"

# Security: Limit request size to prevent resource exhaustion (DoS)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB limit

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
# Security: Jinja2 automatically escapes variables passed into templates, preventing XSS.
LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
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
    <div>{{ content | safe }}</div>
</body>
</html>
"""

INDEX_TEMPLATE = """
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
"""

ENTRY_TEMPLATE = """
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
"""

HISTORY_TEMPLATE = """
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
"""

def wrap_html(template_str, **kwargs):
    # Security: Render inner content first (escaped by Jinja2), then wrap in layout.
    # The 'safe' filter in LAYOUT is used because the inner content is already escaped.
    inner_html = render_template_string(template_str, **kwargs)
    return render_template_string(LAYOUT, content=inner_html)

@app.route('/')
def home():
    return redirect(url_for('list_entries'))

@app.route('/entries', methods=['GET'])
def list_entries():
    try:
        db = get_db()
        # Security: Parameterized query (though no user input here)
        entries = db.execute('SELECT id, title FROM entries').fetchall()
        return wrap_html(INDEX_TEMPLATE, entries=entries)
    except Exception:
        abort(500)

@app.route('/entries', methods=['POST'])
def create_entry():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        if not data:
            return jsonify({"error": "Invalid request body"}), 400

        title = data.get('title')
        content = data.get('content')
        created_by = data.get('createdBy')

        if not all([title, content, created_by]):
            return jsonify({"error": "Missing required fields"}), 400

        db = get_db()
        cursor = db.cursor()
        # Security: Parameterized SQL to prevent SQL Injection
        cursor.execute('INSERT INTO entries (title, content, last_modified_by) VALUES (?, ?, ?)', 
                       (title, content, created_by))
        entry_id = cursor.lastrowid
        
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
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/entries/<int:entryId>', methods=['GET'])
def get_entry(entryId):
    try:
        db = get_db()
        # Security: Parameterized SQL
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
        
        if "text/html" in request.headers.get('Accept', 'text/html'):
            return wrap_html(ENTRY_TEMPLATE, entry=entry_data)
        
        return jsonify(entry_data)
    except Exception as e:
        if hasattr(e, 'code') and e.code == 404:
            abort(404)
        abort(500)

@app.route('/entries/<int:entryId>', methods=['POST', 'PUT'])
def update_entry(entryId):
    try:
        # Handle HTML form simulating PUT
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

        if not data:
            return jsonify({"error": "Invalid request body"}), 400

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
        # Security: Parameterized SQL
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
    except Exception as e:
        if hasattr(e, 'code') and e.code == 404:
            abort(404)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/entries/<int:entryId>/edits', methods=['GET'])
def get_history(entryId):
    try:
        db = get_db()
        # Security: Parameterized SQL
        entry = db.execute('SELECT title FROM entries WHERE id = ?', (entryId,)).fetchone()
        if not entry:
            abort(404)
        
        edits = db.execute('SELECT * FROM edits WHERE entry_id = ? ORDER BY modified_at DESC', (entryId,)).fetchall()
        return wrap_html(HISTORY_TEMPLATE, title=entry['title'], edits=edits)
    except Exception as e:
        if hasattr(e, 'code') and e.code == 404:
            abort(404)
        abort(500)

# Security: Generic error handler to prevent leaking stack traces
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    # Security: debug=False to prevent leaking internal details via the debugger
    app.run(host='0.0.0.0', port=5000, debug=False)