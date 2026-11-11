import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify

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
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .message { border-bottom: 1px solid #ccc; padding: 10px 0; }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; }
        .meta { font-size: 0.8em; color: #666; }
        .form-box { background: #f4f4f4; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        input, textarea { display: block; width: 100%; margin-bottom: 10px; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="POST" id="postForm">
            <input type="text" name="username" placeholder="Username" required>
            <textarea name="content" placeholder="Message content" required></textarea>
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
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    sort = request.args.get('sort', 'DESC').upper()

    if sort not in ['ASC', 'DESC']:
        sort = 'DESC'

    conn = get_db_connection()
    query = f"SELECT username, content, timestamp FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
    messages = conn.execute(query, (limit, offset)).fetchall()
    conn.close()

    return render_template_string(HTML_TEMPLATE, messages=messages)

@app.route('/messages', methods=['POST'])
def post_message():
    # The OpenAPI schema specifies application/json, but for a webapp we handle both
    # to allow the HTML form to work while remaining compliant with the API spec.
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    username = data.get('username')
    content = data.get('content')

    if not username or not content:
        return jsonify({"error": "Invalid input"}), 400

    conn = get_db_connection()
    conn.execute('INSERT INTO messages (username, content) VALUES (?, ?)', (username, content))
    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify({"status": "Successful operation"}), 200
    else:
        # Redirect back to the forum page for the web UI
        from flask import redirect
        return redirect('/messages')

@app.route('/')
def index():
    from flask import redirect
    return redirect('/messages')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)