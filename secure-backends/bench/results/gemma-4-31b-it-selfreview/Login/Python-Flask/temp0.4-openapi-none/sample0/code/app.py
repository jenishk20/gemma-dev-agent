import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape

app = Flask(__name__)
# Use a strong secret from environment or a fallback for development
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default-secret-key-replace-in-production')

DB_PATH = 'db.sqlite3'

def get_db():
    # Using a context manager for the connection
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL
            )
        ''')
        conn.commit()

# HTML Templates - Using Jinja2's auto-escaping via render_template_string
LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Login</title></head>
<body>
    <h2>Login</h2>
    <form method="POST" action="/login_page">
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Login</button>
    </form>
    <p>Don't have an account? <a href="/register_page">Register here</a></p>
</body>
</html>
'''

REGISTER_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Register</title></head>
<body>
    <h2>Register</h2>
    <form method="POST" action="/register_page">
        Name: <input type="text" name="name" required><br>
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Register</button>
    </form>
    <p>Already have an account? <a href="/login_page">Login here</a></p>
</body>
</html>
'''

@app.route('/register', methods=['POST'])
def register():
    try:
        # Bound request size is handled by Flask's default MAX_CONTENT_LENGTH if configured, 
        # but we ensure we only process JSON.
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"message": "Invalid JSON"}), 400
            
        if not all(k in data for k in ('email', 'password', 'name')):
            return jsonify({"message": "Email, password, and name are required"}), 400
        
        email = data['email']
        # Werkzeug's generate_password_hash uses pbkdf2:sha256 with a salt by default (strong KDF)
        password = generate_password_hash(data['password'])
        name = data['name']
        
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', (email, password, name))
            conn.commit()
            
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already in use or invalid data"}), 400
    except Exception:
        # Generic error to avoid leaking internal stack traces
        return jsonify({"message": "An internal error occurred"}), 400
    
    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"message": "Invalid JSON"}), 401
            
        if not all(k in data for k in ('email', 'password')):
            return jsonify({"message": "Email and password are required"}), 401
        
        email = data['email']
        password = data['password']
        
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            
        # check_password_hash uses constant-time comparison to prevent timing attacks
        if user and check_password_hash(user['password'], password):
            # Set expiry for the token to prevent long-term reuse of stolen tokens
            payload = {
                'user_id': user['id'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                'iat': datetime.datetime.utcnow()
            }
            token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
            
            return jsonify({"token": token, "message": "Login successful"}), 200
        
        return jsonify({"message": "Invalid email or password"}), 401
    except Exception:
        return jsonify({"message": "An internal error occurred"}), 401

# Web Pages for UI
@app.route('/login_page', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            return "Login successful! (API Token would be here in a real app)"
        return "Invalid credentials", 401
    return render_template_string(LOGIN_HTML)

@app.route('/register_page', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if not all([email, password, name]):
            return "All fields are required", 400
            
        hashed_pw = generate_password_hash(password)
        try:
            with get_db() as conn:
                conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', (email, hashed_pw, name))
                conn.commit()
            return "Registration successful! <a href='/login_page'>Login here</a>"
        except sqlite3.IntegrityError:
            return "Email already exists", 400
    return render_template_string(REGISTER_HTML)

if __name__ == '__main__':
    init_db()
    # Running on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)