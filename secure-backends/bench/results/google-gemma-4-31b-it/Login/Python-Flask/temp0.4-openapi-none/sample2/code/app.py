import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_PATH = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
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

# HTML Templates
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; }
        .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        .form-group { margin-bottom: 1rem; }
        label { display: block; margin-bottom: .5rem; }
        input { width: 100%; padding: 8px; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .error { color: red; font-size: 0.8rem; margin-bottom: 1rem; }
        .success { color: green; font-size: 0.8rem; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <div class="card">
        <h2>{{ title }}</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        {% if success %}<div class="success">{{ success }}</div>{% endif %}
        <form method="POST" action="{{ action }}">
            {% for field in fields %}
                <div class="form-group">
                    <label>{{ field }}</label>
                    <input type="{{ 'password' if field == 'Password' else 'text' }}" name="{{ field.lower() }}" required>
                </div>
            {% endfor %}
            <button type="submit">Submit</button>
        </form>
        <p style="text-align: center; font-size: 0.9rem;">
            {{ link_text }} <a href="{{ link_url }}">{{ link_label }}</a>
        </p>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE, 
                                title="Login", 
                                action="/login", 
                                fields=["Email", "Password"], 
                                link_text="Don't have an account?", 
                                link_url="/register", 
                                link_label="Register here")

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        # This handles the HTML form submission for the UI
        data = {
            "email": request.form.get("email"),
            "password": request.form.get("password"),
            "name": request.form.get("name")
        }
        return register_api(data)
    
    return render_template_string(BASE_TEMPLATE, 
                                title="Register", 
                                action="/register", 
                                fields=["Name", "Email", "Password"], 
                                link_text="Already have an account?", 
                                link_url="/", 
                                link_label="Login here")

# API Implementation based on OpenAPI Schema

@app.route('/register', methods=['POST'])
def register_api():
    # Support both JSON and Form data for the webapp
    data = request.get_json() if request.is_json else request.form
    
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not email or not password or not name:
        return jsonify({"message": "Email, password, and name are required"}), 400

    hashed_pw = generate_password_hash(password)
    
    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', 
                        (email, hashed_pw, name))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already in use or invalid data"}), 400

    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login_api():
    data = request.get_json() if request.is_json else request.form
    
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

    if user and check_password_hash(user['password'], password):
        token = jwt.encode(
            {'user_id': user['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
            app.secret_key,
            algorithm="HS256"
        )
        return jsonify({"token": token, "message": "Login successful"}), 200
    
    return jsonify({"message": "Invalid email or password"}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)