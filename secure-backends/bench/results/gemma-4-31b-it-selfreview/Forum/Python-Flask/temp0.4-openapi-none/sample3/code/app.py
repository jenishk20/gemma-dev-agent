import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify, redirect

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_NAME = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# HTML Template for the forum. 
# Jinja2 automatically escapes variables ({{ msg.username }}), preventing XSS.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .message { border-bottom: 1px solid #ccc; padding: 10px 0; }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; white-space: pre-wrap; }
        .meta { font-size: 0.8em; color: #666; }
        .form-box { background: #f4f4f4; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        input, textarea { display: block; width: 100%; margin-bottom: 10px; box-sizing: border-box; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="POST">
            <input type="text" name="username" placeholder="Username" required maxlength="100">
            <textarea name="content" placeholder="Message content" required maxlength="2000"></textarea>
            <button type="submit">Post</button>
        </form>
    </div>

    <hr>

    <div class="pagination">
        <a href="/messages?sort=ASC">Oldest First</a> | 
        <a href="/messages?sort=DESC">Newest First</a>
    </div>

    <div class="messages">
        {% for msg in messages %}
        <div class="message">
            <div class="username">{{ msg.username }}</div>
            <div class="content">{{ msg.content }}</div>
            <div class="meta">{{ msg.timestamp }}</div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route('/messages', methods=['GET'])
def get_messages():
    try:
        # Resource Exhaustion: Bound the limit to prevent huge memory allocations
        limit = request.args.get('limit', 10, type=int)
        if limit < 1 or limit > 100:
            limit = 10
            
        offset = request.args.get('offset', 0, type=int)
        if offset < 0:
            offset = 0
            
        sort = request.args.get('sort', 'DESC').upper()
        if sort not in ['ASC', 'DESC']:
            sort = 'DESC'

        conn = get_db_connection()
        # SQL Injection: 'sort' is validated against a whitelist. 
        # limit and offset are passed as parameterized values.
        query = f"SELECT username, content, timestamp FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
        messages = conn.execute(query, (limit, offset)).fetchall()
        conn.close()

        return render_template_string(HTML_TEMPLATE, messages=messages)
    except Exception:
        # Error Handling: Generic error to avoid leaking stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/messages', methods=['POST'])
def post_message():
    try:
        # Resource Exhaustion: Limit request body size
        if request.content_length > 10 * 1024: # 10KB limit
            return jsonify({"error": "Request too large"}), 400

        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        if not data:
            return jsonify({"error": "Invalid input"}), 400

        username = data.get('username')
        content = data.get('content')

        # Validation: Ensure inputs are strings and not empty
        if not isinstance(username, str) or not isinstance(content, str):
            return jsonify({"error": "Invalid input"}), 400
            
        username = username.strip()
        content = content.strip()

        if not username or not content:
            return jsonify({"error": "Invalid input"}), 400

        # SQL Injection: Use parameterized query
        conn = get_db_connection()
        conn.execute('INSERT INTO messages (username, content) VALUES (?, ?)', (username, content))
        conn.commit()
        conn.close()

        if request.is_json:
            return jsonify({"status": "Successful operation"}), 200
        else:
            return redirect('/messages')
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/')
def index():
    return redirect('/messages')

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)