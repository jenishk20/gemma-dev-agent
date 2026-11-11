import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, abort

app = Flask(__name__)
DATABASE = 'db.sqlite3'

# HTML Templates
# Note: Jinja2 automatically escapes variables passed to render_template_string, 
# protecting against XSS.
LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Wiki App</title>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-box { border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .meta { font-size: 0.8em; color: #666; }
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
            <div class="meta"><strong>{{ edit[3] }}</strong> on {{ edit[4] }} - <em>{{ edit[5] }}</em></div>
            <div style="white-space: pre-wrap; font-family: monospace; font-size: 0.9em; margin-top: 10px;">
                {{ edit[2] }}
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
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        user = request.form.get('createdBy', '').strip()
        
        if not title or not content or not user:
            return "Missing fields", 400
            
        db = get_db()
        now = datetime.now().isoformat()
        try:
            cursor = db.cursor()
            cursor.execute("INSERT INTO entries (title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?)", 
                           (title, content, user, now))
            entry_id = cursor.lastrowid
            cursor.execute("INSERT INTO edits (entry_id, content, contributor, timestamp, summary) VALUES (?, ?, ?, ?, ?)", 
                           (entry_id, content, user, now, "Initial creation"))
            db.commit()
        except Exception:
            return "Internal Server Error", 500
        finally:
            db.close()
        return redirect(url_for('list_entries'))

    db = get_db()
    try:
        entries = db.execute("SELECT id, title FROM entries").fetchall()
    except Exception:
        return "Internal Server Error", 500
    finally:
        db.close()
    return render_template_string(INDEX_TPL, entries=entries)

@app.route('/entries/<int:entryId>', methods=['GET', 'POST'])
def get_entry(entryId):
    db = get_db()
    try:
        entry = db.execute("SELECT * FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            abort(404)

        if request.method == 'POST':
            content = request.form.get('content', '').strip()
            user = request.form.get('modifiedBy', '').strip()
            summary = request.form.get('summary', '').strip()
            
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
    except Exception:
        return "Internal Server Error", 500
    finally:
        db.close()

@app.route('/entries/<int:entryId>/edits', methods=['GET'])
def view_history(entryId):
    db = get_db()
    try:
        entry = db.execute("SELECT title FROM entries WHERE id = ?", (entryId,)).fetchone()
        if not entry:
            abort(404)
        
        edits = db.execute("SELECT * FROM edits WHERE entry_id = ? ORDER BY timestamp DESC", (entryId,)).fetchall()
        edit_list = [tuple(row) for row in edits]
        return render_template_string(HISTORY_TPL, title=entry['title'], edits=edit_list, entry_id=entryId)
    except Exception:
        return "Internal Server Error", 500
    finally:
        db.close()

@app.route('/api/entries', methods=['POST'])
def api_create_entry():
    # Bound request size is handled by Flask's default MAX_CONTENT_LENGTH if configured, 
    # otherwise we check for JSON validity.
    data = request.get_json(silent=True)
    if data is None or not all(k in data for k in ('title', 'content', 'createdBy')):
        return jsonify({"error": "Invalid input"}), 400
    
    # Basic validation to prevent extremely large inputs from causing resource exhaustion
    if len(str(data.get('title', '')) ) > 1000 or len(str(data.get('content', ''))) > 100000:
        return jsonify({"error": "Input too large"}), 400

    db = get_db()
    now = datetime.now().isoformat()
    try:
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
    except Exception:
        return jsonify({"error": "Internal Server Error"}), 500
    finally:
        db.close()

@app.route('/api/entries/<int:entryId>', methods=['PUT'])
def api_update_entry(entryId):
    data = request.get_json(silent=True)
    if data is None or not all(k in data for k in ('content', 'modifiedBy', 'summary')):
        return jsonify({"error": "Invalid input"}), 400
    
    if len(str(data.get('content', ''))) > 100000:
        return jsonify({"error": "Input too large"}), 400

    db = get_db()
    try:
        entry = db.execute("SELECT title FROM entries WHERE id = ?", (entryId,)).fetchone()
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
    except Exception:
        return jsonify({"error": "Internal Server Error"}), 500
    finally:
        db.close()

if __name__ == '__main__':
    init_db()
    # Setting threaded=True and using the default Flask server for this task.
    # In production, a WSGI server like Gunicorn would be used.
    app.run(host='0.0.0.0', port=5000)