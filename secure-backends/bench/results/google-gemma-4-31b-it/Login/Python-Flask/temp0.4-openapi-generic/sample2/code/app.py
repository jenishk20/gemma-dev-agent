import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_for_dev")

DB_PATH = "db.sqlite3"

# --- Database Setup ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL
            )
        ''')
        conn.commit()

init_db()

# --- HTML Templates ---
# Using render_template_string to keep everything in one file
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; }
        .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 8px; margin: 10px 0; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .error { color: red; font-size: 0.8rem; margin-bottom: 10px; }
        .success { color: green; font-size: 0.8rem; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>{{ title }}</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        {% if success %}<div class="success">{{ success }}</div>{% endif %}
        <form method="POST">
            {% for field in fields %}
                <label>{{ field.capitalize() }}</label>
                <input type="{{ 'password' if field == 'password' else 'text' }}" name="{{ field }}" required>
            {% endfor %}
            <button type="submit">Submit</button>
        </form>
        <p style="font-size: 0.8rem; text-align: center; margin-top: 15px;">
            {% if title == 'Login' %}
                Don't have an account? <a href="/register_page">Register here</a>
            {% else %}
                Already have an account? <a href="/login_page">Login here</a>
            {% endif %}
        </p>
    </div>
</body>
</html>
"""

# --- API Logic ---

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'password', 'name')):
        return jsonify({"message": "Invalid data"}), 400
    
    email = data['email']
    password = data['password']
    name = data['name']
    
    hashed_pw = generate_password_hash(password)
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", (email, hashed_pw, name))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already in use"}), 400
        
    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'password')):
        return jsonify({"message": "Invalid email or password"}), 401
    
    email = data['email']
    password = data['password']
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT password FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        
    if row and check_password_hash(row[0], password):
        token = jwt.encode({
            'user': email,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.secret_key, algorithm="HS256")
        
        return jsonify({"token": token, "message": "Login successful"}), 200
    
    return jsonify({"message": "Invalid email or password"}), 401

# --- Web Pages (UI) ---

@app.route('/login_page', methods=['GET', 'POST'])
def login_page():
    error = None
    success = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Simulate the API call internally
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT password FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row and check_password_hash(row[0], password):
                success = "Login successful! (Token generated in API)"
            else:
                error = "Invalid email or password"
                
    return render_template_string(BASE_HTML, title="Login", fields=['email', 'password'], error=error, success=success)

@app.route('/register_page', methods=['GET', 'POST'])
def register_page():
    error = None
    success = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        hashed_pw = generate_password_hash(password)
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", (email, hashed_pw, name))
                conn.commit()
                success = "Registration successful!"
        except sqlite3.IntegrityError:
            error = "Email already in use"
            
    return render_template_string(BASE_HTML, title="Register", fields=['email', 'password', 'name'], error=error, success=success)

@app.route('/')
def index():
    return '<a href="/login_page">Login Page</a> | <a href="/register_page">Register Page</a>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)