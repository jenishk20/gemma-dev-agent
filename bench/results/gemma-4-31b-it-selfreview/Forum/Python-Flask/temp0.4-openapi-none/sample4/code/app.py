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

# HTML Template for the forum
# Note: Jinja2's render_template_string automatically escapes variables 
# passed into the template, preventing XSS.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .message { border-bottom: 1px solid #ccc; padding: 10px 0; }
        .username { font-weight: bold; color: #555; }
        .content { margin-top: 5px; white-space: pre-wrap; }
        .form-box { background: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        input, textarea { display: block; margin-bottom: 10px; width: 100%; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="post">
            <input type="text" name="username" placeholder="Username" required maxlength="100">
            <textarea name="content" placeholder="Message content" required maxlength="2000"></textarea>
            <button type="submit">Post</button>
        </form>
    </div>

    <div class="messages">
        {% for msg in messages %}
            <div class="message">
                <span class="username">{{ msg.username }}</span> 
                <small style="color: #999;">{{ msg.timestamp }}</small>
                <div class="content">{{ msg.content }}</div>
            </div>
        {% endfor %}
    </div>
    
    <div style="margin-top: 20px;">
        <a href="/messages?sort=ASC">Oldest First</a> | 
        <a href="/messages?sort=DESC">Newest First</a>
    </div>
</body>
</html>
"""

@app.route('/messages', methods=['GET'])
def get_messages():
    try:
        # Resource exhaustion: Bound the limit to a reasonable maximum (e.g., 100)
        limit_val = request.args.get('limit', default=10, type=int)
        if limit_val < 0: limit_val = 0
        if limit_val > 100: limit_val = 100
        
        offset_val = request.args.get('offset', default=0, type=int)
        if offset_val < 0: offset_val = 0
        
        sort = request.args.get('sort', default='DESC').upper()
        # SQL Injection prevention: Use a whitelist for the ORDER BY clause 
        # as parameters cannot be used for column names or directions.
        if sort not in ['ASC', 'DESC']:
            sort = 'DESC'

        conn = get_db_connection()
        # Parameterized query for limit and offset
        query = f"SELECT username, content, timestamp FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
        messages = conn.execute(query, (limit_val, offset_val)).fetchall()
        conn.close()

        return render_template_string(HTML_TEMPLATE, messages=messages)
    except Exception:
        # Error handling: Return generic error to avoid leaking internals
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/messages', methods=['POST'])
def post_message():
    # Resource exhaustion: Limit request body size (Flask does this via MAX_CONTENT_LENGTH)
    # We manually check for existence and types.
    if request.is_json:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400
    else:
        data = request.form

    if data is None:
        return jsonify({"error": "Invalid input"}), 400

    username = data.get('username')
    content = data.get('content')

    # Validate input types and presence
    if not isinstance(username, str) or not isinstance(content, str):
        return jsonify({"error": "Invalid input"}), 400
    
    if not username.strip() or not content.strip():
        return jsonify({"error": "Invalid input"}), 400

    # Resource exhaustion: Prevent excessively large strings from hitting the DB
    if len(username) > 100 or len(content) > 2000:
        return jsonify({"error": "Input too long"}), 400

    try:
        conn = get_db_connection()
        # SQL Injection prevention: Use parameterized query
        conn.execute('INSERT INTO messages (username, content) VALUES (?, ?)', (username, content))
        conn.commit()
        conn.close()
    except Exception:
        return jsonify({"error": "Internal Server Error"}), 500

    if not request.is_json:
        return redirect('/messages')
    
    return jsonify({"status": "Successful operation"}), 200

# Set a maximum content length to prevent DoS via large payloads
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 # 2MB

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)