import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")
DB_PATH = "db.sqlite3"

# Database initialization
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

# Helper to get DB connection
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# JWT Utility
def create_token(email):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow(),
        'sub': email
    }
    return jwt.encode(payload, app.secret_key, algorithm='HS256')

# HTML Templates for the frontend
LOGIN_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
    <h2>Login</h2>
    <form method="POST" action="/login_ui">
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Login</button>
    </form>
    <p>Don't have an account? <a href="/register_ui">Register here</a></p>
</body>
</html>
'''

REGISTER_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>Register</title></head>
<body>
    <h2>Register</h2>
    <form method="POST" action="/register_ui">
        Name: <input type="text" name="name" required><br>
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Register</button>
    </form>
    <p>Already have an account? <a href="/login_ui">Login here</a></p>
</body>
</html>
'''

# --- API Endpoints (OpenAPI Specification) ---

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'password', 'name')):
        return jsonify({"message": "Email already in use or invalid data"}), 400
    
    email = data['email']
    password = data['password']
    name = data['name']
    
    hashed_pw = generate_password_hash(password)
    
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", 
                        (email, hashed_pw, name))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already in use or invalid data"}), 400
    
    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'password')):
        return jsonify({"message": "Invalid email or password"}), 401
    
    email = data['email']
    password = data['password']
    
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        
    if user and check_password_hash(user['password'], password):
        token = create_token(email)
        return jsonify({"token": token, "message": "Login successful"}), 200
    
    return jsonify({"message": "Invalid email or password"}), 401

# --- UI Endpoints (For browser access) ---

@app.route('/login_ui', methods=['GET', 'POST'])
def login_ui():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            return "<h1>Login Successful!</h1><p>You are now authenticated.</p><a href='/login_ui'>Back</a>"
        return "<h1>Login Failed</h1><a href='/login_ui'>Try again</a>", 401
    
    return render_template_string(LOGIN_PAGE)

@app.route('/register_ui', methods=['GET', 'POST'])
def register_ui():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if not email or not password or not name:
            return "Missing fields", 400
            
        hashed_pw = generate_password_hash(password)
        try:
            with get_db() as conn:
                conn.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", 
                            (email, hashed_pw, name))
                conn.commit()
        except sqlite3.IntegrityError:
            return "Email already exists", 400
            
        return "<h1>Registration Successful!</h1><a href='/login_ui'>Login now</a>"
    
    return render_template_string(REGISTER_PAGE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)