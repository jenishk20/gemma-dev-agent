import os
import sqlite3
import datetime
import jwt
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

# Configuration
APP_SECRET = os.environ.get("APP_SECRET", "default_secret_key_change_me")
DB_NAME = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS secrets (
                username TEXT PRIMARY KEY,
                secret_value TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        ''')
        conn.commit()

# Token helper
def create_token(username):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow(),
        'sub': username
    }
    return jwt.encode(payload, APP_SECRET, algorithm='HS256')

def decode_token(token):
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=['HS256'])
        return payload['sub']
    except (jwt.ExpiredBypass, jwt.InvalidTokenError, Exception):
        return None

# Middleware for Bearer Auth
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"message": "Invalid authentication token"}), 401
        
        token = auth_header.split(" ")[1]
        username = decode_token(token)
        if not username:
            return jsonify({"message": "Invalid authentication token"}), 401
        
        return f(username, *args, **kwargs)
    return decorated

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'username', 'password')):
        return jsonify({"message": "Invalid data"}), 400
    
    email = data['email']
    username = data['username']
    password = data['password']

    hashed_pw = generate_password_hash(password)

    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', 
                        (username, email, hashed_pw))
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

    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    
    if user and check_password_hash(user['password'], password):
        token = create_token(user['username'])
        return jsonify({"token": token, "message": "Login successful"}), 200
    
    return jsonify({"message": "Invalid email or password"}), 401

@app.route('/set_secret', methods=['POST'])
@token_required
def set_secret(auth_user):
    data = request.get_json()
    if not data or not all(k in data for k in ('username', 'secret')):
        return jsonify({"message": "Invalid data"}), 400
    
    target_username = data['username']
    secret_text = data['secret']

    # Security: Users can only set secrets for their own account
    if auth_user != target_username:
        return jsonify({"message": "Unauthorized to set secret for this user"}), 401

    with get_db_connection() as conn:
        conn.execute('INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)', 
                    (target_username, secret_text))
        conn.commit()

    return jsonify({"message": "Secret has been set successfully"}), 200

@app.route('/get_secret', methods=['GET'])
@token_required
def get_secret(auth_user):
    username = request.args.get('username')
    if not username:
        return jsonify({"message": "Username is required"}), 400

    # Security: Users can only retrieve their own secret
    if auth_user != username:
        return jsonify({"message": "Invalid authentication token"}), 401

    with get_db_connection() as conn:
        row = conn.execute('SELECT secret_value FROM secrets WHERE username = ?', (username,)).fetchone()
    
    if row:
        return jsonify({"secret": row['secret_value']}), 200
    else:
        return jsonify({"secret": "No secret found for this user"}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)