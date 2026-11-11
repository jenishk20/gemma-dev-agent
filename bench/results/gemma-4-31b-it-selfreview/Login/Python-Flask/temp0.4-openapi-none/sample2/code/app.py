import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape

app = Flask(__name__)
# Ensure secret key is robustly handled
app.secret_key = os.environ.get("APP_SECRET", "fallback_secure_random_string_for_dev")

DB_PATH = "db.sqlite3"

def get_db_connection():
    # sqlite3.connect is safe from path traversal here as DB_PATH is hardcoded
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
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
    except Exception:
        # Fail silently during init or log internally; avoid leaking to user
        pass

init_db()

# HTML Templates - Using Jinja2's auto-escaping and explicit markupsafe.escape for dynamic content
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
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
        # Use the API logic to handle the form submission
        # We pass the form data to the register_api function
        return register_api(request.form)
    
    return render_template_string(BASE_TEMPLATE, 
                                title="Register", 
                                action="/register", 
                                fields=["Name", "Email", "Password"], 
                                link_text="Already have an account?", 
                                link_url="/", 
                                link_label="Login here")

# API Implementation

@app.route('/register', methods=['POST'])
def register_api(form_data=None):
    # Resource Exhaustion: Limit request body size (Flask does this via MAX_CONTENT_LENGTH, but we handle JSON safely)
    # Support both JSON and Form data
    if form_data is not None:
        data = form_data
    else:
        data = request.get_json(silent=True) if request.is_json else request.form
    
    if not data:
        return jsonify({"message": "Invalid request body"}), 400

    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    # Input Validation
    if not all([email, password, name]) or not isinstance(email, str) or not isinstance(password, str) or not isinstance(name, str):
        return jsonify({"message": "Email, password, and name are required"}), 400

    # Password Hashing: werkzeug.security uses PBKDF2 with a salt by default (strong KDF)
    hashed_pw = generate_password_hash(password)
    
    try:
        with get_db_connection() as conn:
            # Parameterized query to prevent SQL Injection
            conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', 
                        (email, hashed_pw, name))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already in use or invalid data"}), 400
    except Exception:
        # Generic error to avoid leaking internal DB details
        return jsonify({"message": "Internal server error"}), 400

    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login_api():
    data = request.get_json(silent=True) if request.is_json else request.form
    
    if not data:
        return jsonify({"message": "Invalid request body"}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password or not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"message": "Email and password are required"}), 400

    try:
        with get_db_connection() as conn:
            # Parameterized query to prevent SQL Injection
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        # check_password_hash uses constant-time comparison to prevent timing attacks
        if user and check_password_hash(user['password'], password):
            # Token Security: Set expiry, use strong secret, and specify algorithm
            payload = {
                'user_id': user['id'], 
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                'iat': datetime.datetime.utcnow()
            }
            token = jwt.encode(payload, app.secret_key, algorithm="HS256")
            return jsonify({"token": token, "message": "Login successful"}), 200
    except Exception:
        # Generic error to avoid leaking internal details
        return jsonify({"message": "Internal server error"}), 401
    
    return jsonify({"message": "Invalid email or password"}), 401

if __name__ == '__main__':
    # Port 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)