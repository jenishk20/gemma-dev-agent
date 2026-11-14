import sqlite3
import uuid
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, jsonify, abort

app = Flask(__name__)

DATABASE = 'db.sqlite3'

def get_db():
    conn = sqlite3.connect(DATABASE)
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
                content TEXT,
                modified_by TEXT,
                summary TEXT,
                modified_at TEXT,
                FOREIGN KEY(entry_id) REFERENCES entries(id)
            )
        ''')
        conn.commit()

# HTML Templates
LAYOUT = '''
<!DOCTYPE html>
<html>
<head>
    <title>Wiki App</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .entry-card { border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 4px; }
        .diff { background: #f9f9f9; border-left: 3px solid #ccc; padding: 10px; margin: 10px 0; white-space: pre-wrap; }
        .meta { font-size: 0.8em; color: #666; }
        form div { margin-bottom: 10px; }
        label { display: block; font-weight: bold; }
        input[type="text"], textarea { width: 100%; padding: 8px; box-sizing: border-box; }
        textarea { height: 200px; }
        .btn { padding: 10px 15px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 3px; }
    </style>
</head>
<body>
    <nav>
        <a href="/">🏠 Home</a> | <a href="/create">➕ New Entry</a>
    </nav>
    {% block content %}{% endblock %}
</body>
</html>
'''

INDEX_TPL = '''
{% extends "layout" %}
{% block content %}
    <h1>Wiki Entries</h1>
    {% if entries %}
        {% for entry in entries %}
            <div class="entry-card">
                <h3><a href="/entries/{{ entry.id }}">{{ entry.title }}</a></h3>
                <p class="meta">Last edited by {{ entry.last_modified_by }} on {{ entry.last_modified_at }}</p>
            </div>
        {% endfor %}
    {% else %}
        <p>No entries found. Be the first to create one!</p>
    {% endif %}
{% endblock %}
'''

ENTRY_TPL = '''
{% extends "layout" %}
{% block content %}
    <h1>{{ entry.title }}</h1>
    <div style="white-space: pre-wrap; border: 1px solid #eee; padding: 20px; background: #fff;">{{ entry.content }}</div>
    <p class="meta">Last modified by {{ entry.last_modified_by }} at {{ entry.last_modified_at }}</p>
    <hr>
    <a href="/entries/{{ entry.id }}/edit" class="btn">Edit this page</a>
    <a href="/entries/{{ entry.id }}/edits" class="btn" style="background:#6c757d">View History</a>
{% endblock %}
'''

EDIT_TPL = '''
{% extends "layout" %}
{% block content %}
    <h1>Edit Entry: {{ title }}</h1>
    <form method="POST" action="/entries/{{ entry_id }}/update">
        <div>
            <label>Content</label>
            <textarea name="content" required>{{ content }}</textarea>
        </div>
        <div>
            <label>Your Name</label>
            <input type="text" name="modifiedBy" required>
        </div>
        <div>
            <label>Edit Summary</label>
            <input type="text" name="summary" required placeholder="What did you change?">
        </div>
        <button type="submit" class="btn">Save Changes</button>
    </form>
{% endblock %}
'''

HISTORY_TPL = '''
{% extends "layout" %}
{% block content %}
    <h1>Edit History: {{ title }}</h1>
    {% for edit in edits %}
        <div class="entry-card">
            <strong>{{ edit.modified_by }}</strong> - {{ edit.modified_at }}<br>
            <em>Summary: {{ edit.summary }}</em>
            <div class="diff">{{ edit.content }}</div>
        </div>
    {% endfor %}
    {% if not edits %}<p>No history available.</p>{% endif %}
{% endblock %}
'''

CREATE_TPL = '''
{% extends "layout" %}
{% block content %}
    <h1>Create New Entry</h1>
    <form method="POST" action="/entries/create">
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
        <button type="submit" class="btn">Create Entry</button>
    </form>
{% endblock %}
'''

@app.context_processor
def inject_layout():
    return {'layout': LAYOUT}

@app.route('/')
def index():
    db = get_db()
    entries = db.execute('SELECT * FROM entries').fetchall()
    return render_template_string(INDEX_TPL, entries=entries)

@app.route('/create', methods=['GET', 'POST'])
def create_entry_ui():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        user = request.form.get('createdBy')
        
        entry_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        db = get_db()
        db.execute('INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)',
                   (entry_id, title, content, user, now))
        db.execute('INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)',
                   (entry_id, content, user, 'Initial creation', now))
        db.commit()
        return redirect(url_for('index'))
    
    return render_template_string(CREATE_TPL)

@app.route('/entries', methods=['GET', 'POST'])
def entries_api():
    if request.method == 'GET':
        # The OpenAPI spec says /entries GET returns text/html
        return index()
    
    if request.method == 'POST':
        data = request.json
        if not data or not all(k in data for k in ('title', 'content', 'createdBy')):
            return jsonify({"error": "Missing required fields"}), 400
        
        entry_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        db = get_db()
        db.execute('INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?, ?, ?, ?, ?)',
                   (entry_id, data['title'], data['content'], data['createdBy'], now))
        db.execute('INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)',
                   (entry_id, data['content'], data['createdBy'], 'Initial creation', now))
        db.commit()
        
        return jsonify({
            "id": entry_id,
            "title": data['title'],
            "content": data['content'],
            "lastModifiedBy": data['createdBy'],
            "lastModifiedAt": now
        }), 201

@app.route('/entries/<entry_id>', methods=['GET'])
def get_entry(entry_id):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()
    if not entry:
        abort(404)
    
    # Return HTML for the webapp
    return render_template_string(ENTRY_TPL, entry=entry)

@app.route('/entries/<entry_id>/edit', methods=['GET'])
def edit_entry_ui(entry_id):
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()
    if not entry:
        abort(404)
    return render_template_string(EDIT_TPL, entry_id=entry_id, title=entry['title'], content=entry['content'])

@app.route('/entries/<entry_id>/update', methods=['POST'])
def update_entry_ui(entry_id):
    content = request.form.get('content')
    user = request.form.get('modifiedBy')
    summary = request.form.get('summary')
    
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()
    if not entry:
        abort(404)
        
    now = datetime.now().isoformat()
    db.execute('UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?',
               (content, user, now, entry_id))
    db.execute('INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)',
               (entry_id, content, user, summary, now))
    db.commit()
    return redirect(url_for('get_entry', entry_id=entry_id))

@app.route('/entries/<entry_id>', methods=['PUT'])
def update_entry_api(entry_id):
    data = request.json
    if not data or not all(k in data for k in ('content', 'modifiedBy', 'summary')):
        return jsonify({"error": "Missing required fields"}), 400
    
    db = get_db()
    entry = db.execute('SELECT * FROM entries WHERE id = ?', (entry_id,)).fetchone()
    if not entry:
        abort(404)
        
    now = datetime.now().isoformat()
    db.execute('UPDATE entries SET content = ?, last_modified_by = ?, last_modified_at = ? WHERE id = ?',
               (data['content'], data['modifiedBy'], now, entry_id))
    db.execute('INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?, ?, ?, ?, ?)',
               (entry_id, data['content'], data['modifiedBy'], data['summary'], now))
    db.commit()
    
    return jsonify({
        "id": entry_id,
        "title": entry['title'],
        "content": data['content'],
        "lastModifiedBy": data['modifiedBy'],
        "lastModifiedAt": now
    })

@app.route('/entries/<entry_id>/edits', methods=['GET'])
def get_history(entry_id):
    db = get_db()
    entry = db.execute('SELECT title FROM entries WHERE id = ?', (entry_id,)).fetchone()
    if not entry:
        abort(404)
    
    edits = db.execute('SELECT * FROM edits WHERE entry_id = ? ORDER BY modified_at DESC', (entry_id,)).fetchall()
    return render_template_string(HISTORY_TPL, title=entry['title'], edits=edits)

# To handle the layout template globally
@app.before_request
def setup_templates():
    # This is a hack to make the 'layout' template available to render_template_string
    # since we are not using a filesystem for templates.
    app.jinja_env.globals.update(layout=LAYOUT)

# Override render_template_string to support the layout extension manually 
# since render_template_string doesn't natively support {% extends "layout" %} 
# without a loader.
from jinja2 import Template
def custom_render(template_str, **context):
    # Replace {% extends "layout" %} with the actual layout content
    if '{% extends "layout" %}' in template_str:
        main_content = template_str.replace('{% extends "layout" %}', '').replace('{% block content %}', '').replace('{% endblock %}', '')
        full_template = LAYOUT.replace('{% block content %}{% endblock %}', main_content)
        return Template(full_template).render(**context)
    return Template(template_str).render(**context)

# Patching the app's render_template_string
app.render_template_string = custom_render

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)