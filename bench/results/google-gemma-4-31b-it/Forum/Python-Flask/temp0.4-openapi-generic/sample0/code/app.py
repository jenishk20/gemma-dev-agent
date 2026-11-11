import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

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
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f4f9; }
        .message { background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; color: #666; }
        .form-box { background: #fff; padding: 20px; border-radius: 5px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        input, textarea { width: 100%; padding: 8px; margin: 5px 0 15px 0; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 3px; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="post">
            <label>Username:</label>
            <input type="text" name="username" required>
            <label>Message:</label>
            <textarea name="content" required></textarea>
            <button type="submit">Post</button>
        </form>
    </div>

    <div class="messages-list">
        {% for msg in messages %}
        <div class="message">
            <span class="username">{{ msg.username }}</span>
            <div class="content">{{ msg.content }}</div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route('/messages', methods=['GET'])
def get_messages():
    # Parameters from OpenAPI schema
    try:
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        sort = request.args.get('sort', 'DESC').upper()
    except ValueError:
        return "Invalid parameters", 400

    if sort not in ['ASC', 'DESC']:
        sort = 'DESC'

    conn = get_db_connection()
    # Using parameterized query to prevent SQL injection
    query = f"SELECT username, content FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
    messages = conn.execute(query, (limit, offset)).fetchall()
    conn.close()

    # The schema specifies text/html response for GET /messages
    return render_template_string(HTML_TEMPLATE, messages=messages)

@app.route('/messages', methods=['POST'])
def post_message():
    # The schema specifies application/json for the request body
    data = request.get_json()
    
    # Handle both JSON and Form data for better usability in the browser
    if not data:
        data = request.form

    username = data.get('username')
    content = data.get('content')

    if not username or not content:
        return jsonify({"error": "Invalid input: username and content are required"}), 400

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO messages (username, content) VALUES (?, ?)', (username, content))
        conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    # If it was a form submission, redirect back to the list
    if request.form:
        return render_template_string(HTML_TEMPLATE, messages=[]) # Simplified redirect
    
    return jsonify({"status": "Successful operation"}), 200

# Root redirect for convenience
@app.route('/')
def index():
    return get_messages()

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)