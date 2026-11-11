import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, abort

app = Flask(__name__)
DATABASE = 'db.sqlite3'

# HTML Templates
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
        .diff-add { background-color: #dfd; }
        .diff-rem { background-color: #fdd; }
        textarea { width: 100%; height: 200px; }
        input[type="text"] { width: 100%; padding: 5px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <nav><a href="/">🏠 Home</a> | <a href="/entries">📝 All Entries</a></nav>
    {% block content %}{% endblock %}
</body>
</html>
"""

INDEX_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>Wiki Home</h1>
    <div class="entry-box">
        <h3>Create New Entry</h3>
        <form action="/entries" method="post">
            <input type="text" name="title" placeholder="Title" required><br>
            <input type="text" name="createdBy" placeholder="Your Name" required><br>
            <textarea name="content" placeholder="Content..." required></textarea><br>
            <button type="submit">Create Entry</button>
        </form>
    </div>
    <h2>Existing Entries</h2>
    <ul>
        {% for entry in entries %}
        <li><a href="/entries/{{ entry[0] }}">{{ entry[1] }}</a></li>
        {% endfor %}
    </ul>
{% endblock %}
"""

ENTRY_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>{{ entry[1] }}</h1>
    <div class="meta">Last modified by {{ entry[3] }} on {{ entry[4] }}</div>
    <div style="white-space: pre-wrap; margin: 20px 0; padding: 10px; border: 1px solid #eee;">{{ entry[2] }}</div>
    
    <hr>
    <h3>Edit this page</h3>
    <form action="/entries/{{ entry[0] }}" method="post">
        <input type="text" name="modifiedBy" placeholder="Your Name" required><br>
        <input type="text" name="summary" placeholder="Edit Summary" required><br>
        <textarea name="content" required>{{ entry[2] }}</textarea><br>
        <button type="submit">Save Changes</button>
    </form>
    
    <p><a href="/entries/{{ entry[0] }}/edits">View Revision History</a></p>
{% endblock %}
"""

HISTORY_TPL = """
{% extends "layout" %}
{% block content %}
    <h1>Revision History: {{ title }}</h1>
    {% for edit in edits %}
        <div class="entry-box">
            <div class="meta"><strong>{{ edit[2] }}</strong> on {{ edit[3] }} - <em>{{ edit[4] }}</em></div>
            <div style="white-space: pre-wrap; font-family: monospace; font-size: 0.9em; margin-top: 10px;">
                {{ edit[1] }}
            </div>
        </div>
    {% endfor %}
    <a href="/entries/{{ entry_id }}">Back to Entry</a>
{% endblock %}
"""

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS entries 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, 
             lastModifiedBy TEXT, lastModifiedAt TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS edits 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER, 
             content TEXT, contributor TEXT, timestamp TEXT, summary TEXT,
             FOREIGN KEY(entry_id) REFERENCES entries(id))''')
        conn.commit()

@app.context_processor
def inject_layout():
    return {'layout': LAYOUT}

@app.route('/')
def home():
    return redirect(url_for('list_entries'))

@app.route('/entries', methods=['GET', 'POST'])
def list_entries():
    if request.method == 'POST':
        # Handle form submission for NewEntry
        title = request.form.get('title')
        content = request.form.get('content')
        user = request.form.get('createdBy')
        
        if not title or not content or not user:
            return "Missing fields", 400
            
        db = get_db()
        now = datetime.now().isoformat()
        cursor = db.cursor()
        cursor.execute("INSERT INTO entries (title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?)", 
                       (title, content, user, now))
        entry_id = cursor.lastrowid
        cursor.execute("INSERT INTO edits (entry_id, content, contributor, timestamp, summary) VALUES (?, ?, ?, ?, ?)", 
                       (entry_id, content, user, now, "Initial creation"))
        db.commit()
        return redirect(url_for('list_entries'))

    # Handle GET
    db = get_db()
    entries = db.execute("SELECT id, title FROM entries").fetchall()
    return render_template_string(INDEX_TPL, entries=entries)

@app.route('/entries/<int:entryId>', methods=['GET', 'POST'])
def get_entry(entryId):
    db = get_db()
    entry = db.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
    if not entry:
        abort(404)

    if request.method == 'POST':
        # Handle UpdateEntry
        content = request.form.get('content')
        user = request.form.get('modifiedBy')
        summary = request.form.get('summary')
        
        if not content or not user or not summary:
            return "Missing fields", 400
            
        now = datetime.now().isoformat()
        db.execute("UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?", 
                   (content, user, now, entryId))
        db.execute("INSERT INTO edits (entry_id, content, contributor, timestamp, summary) VALUES (?, ?, ?, ?, ?)", 
                   (entryId, content, user, now, summary))
        db.commit()
        return redirect(url_for('get_entry', entryId=entryId))

    return render_template_string(ENTRY_TPL, entry=entry)

@app.route('/entries/<int:entryId>/edits', methods=['GET'])
def view_history(entryId):
    db = get_db()
    entry = db.execute("SELECT title FROM entries WHERE id = ?", (entryId,)).fetchone()
    if not entry:
        abort(404)
    
    # We fetch edits. To simulate a "diff", we'll just show the content of each version.
    # Real diffing requires complex logic, but the schema asks for a list of edits.
    edits = db.execute("SELECT * FROM edits WHERE entry_id = ? ORDER BY timestamp DESC", (entryId,)).fetchall()
    
    # Convert Row objects to tuples for the template
    edit_list = [tuple(row) for row in edits]
    return render_template_string(HISTORY_TPL, title=entry['title'], edits=edit_list, entry_id=entryId)

# API JSON wrappers to satisfy the OpenAPI schema requirements for POST/PUT
@app.route('/api/entries', methods=['POST'])
def api_create_entry():
    data = request.json
    if not data or not all(k in data for k in ('title', 'content', 'createdBy')):
        return jsonify({"error": "Invalid input"}), 400
    
    db = get_db()
    now = datetime.now().isoformat()
    cursor = db.cursor()
    cursor.execute("INSERT INTO entries (title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?)", 
                   (data['title'], data['content'], data['createdBy'], now))
    entry_id = cursor.lastrowid
    cursor.execute("INSERT INTO edits (entry_id, content, contributor, timestamp, summary) VALUES (?, ?, ?, ?, ?)", 
                   (entry_id, data['content'], data['createdBy'], now, "API creation"))
    db.commit()
    
    return jsonify({
        "id": str(entry_id),
        "title": data['title'],
        "content": data['content'],
        "lastModifiedBy": data['createdBy'],
        "lastModifiedAt": now
    }), 201

@app.route('/api/entries/<int:entryId>', methods=['PUT'])
def api_update_entry(entryId):
    data = request.json
    if not data or not all(k in data for k in ('content', 'modifiedBy', 'summary')):
        return jsonify({"error": "Invalid input"}), 400
    
    db = get_db()
    entry = db.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
    if not entry:
        return jsonify({"error": "Not found"}), 404
        
    now = datetime.now().isoformat()
    db.execute("UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?", 
               (data['content'], data['modifiedBy'], now, entryId))
    db.execute("INSERT INTO edits (entry_id, content, contributor, timestamp, summary) VALUES (?, ?, ?, ?, ?)", 
               (entryId, data['content'], data['modifiedBy'], now, data['summary']))
    db.commit()
    
    return jsonify({
        "id": str(entryId),
        "title": entry['title'],
        "content": data['content'],
        "lastModifiedBy": data['modifiedBy'],
        "lastModifiedAt": now
    }), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)