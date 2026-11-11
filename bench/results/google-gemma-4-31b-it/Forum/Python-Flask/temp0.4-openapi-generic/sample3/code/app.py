import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
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
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f4f9; }
        .message { background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; color: #555; }
        .form-box { background: #fff; padding: 20px; border-radius: 5px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        input, textarea { width: 100%; padding: 8px; margin: 10px 0; box-sizing: border-box; }
        button { background: #007bff; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 3px; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <textarea name="content" placeholder="Message content..." required></textarea>
            <button type="submit">Post</button>
        </form>
    </div>

    <div class="messages">
        {% for msg in messages %}
            <div class="message">
                <span class="username">{{ msg.username }}</span>
                <div class="content">{{ msg.content }}</div>
            </div>
        {% else %}
            <p>No messages yet.</p>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route('/messages', methods=['GET'])
def get_messages():
    # Parameters from OpenAPI schema
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    sort = request.args.get('sort', 'DESC').upper()

    if sort not in ['ASC', 'DESC']:
        sort = 'DESC'

    conn = get_db_connection()
    # Use parameterized query to prevent SQL injection
    query = f"SELECT username, content FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
    messages = conn.execute(query, (limit, offset)).fetchall()
    conn.close()

    # The schema specifies text/html response for GET /messages
    return render_template_string(HTML_TEMPLATE, messages=messages)

@app.route('/messages', methods=['POST'])
def post_message():
    # The schema specifies application/json for the request body
    data = request.get_json(silent=True)
    
    # Support both JSON (as per schema) and Form data (for the HTML UI)
    if data is None:
        data = request.form

    username = data.get('username')
    content = data.get('content')

    if not username or not content:
        return jsonify({"error": "Invalid input: username and content are required"}), 400

    conn = get_db_connection()
    conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (username, content))
    conn.commit()
    conn.close()

    # Redirect back to the forum page to see the new message
    if request.content_type == 'application/json':
        return jsonify({"status": "Successful operation"}), 200
    return request.redirect('/messages')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)