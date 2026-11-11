import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default-secret-key-change-this-in-production')
DB_FILE = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
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
                FOREIGN KEY (username) REFERENCES users (username)
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
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

# Decorator for JWT authentication
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Invalid token format'}), 401

        if not token:
            return jsonify({'message': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_username = data['sub']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid authentication token'}), 401

        return f(current_user_username, *args, **kwargs)
    return decorated

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'username', 'password')):
        return jsonify({'message': 'Invalid data provided'}), 400

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
        return jsonify({'message': 'Email already in use or username taken'}), 400

    return jsonify({'message': 'Registration successful'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'password')):
        return jsonify({'message': 'Invalid request'}), 400

    email = data['email']
    password = data['password']

    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

    if user and check_password_hash(user['password'], password):
        token = create_token(user['username'])
        return jsonify({'token': token, 'message': 'Login successful'}), 200

    return jsonify({'message': 'Invalid email or password'}), 401

@app.route('/set_secret', methods=['POST'])
@token_required
def set_secret(current_user_username):
    data = request.get_json()
    if not data or 'secret' not in data or 'username' not in data:
        return jsonify({'message': 'Invalid request body'}), 400

    target_username = data['username']
    secret_text = data['secret']

    # Security: Only allow users to set secrets for their own account
    if target_username != current_user_username:
        return jsonify({'message': 'Unauthorized to set secret for this user'}), 401

    with get_db_connection() as conn:
        conn.execute('INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)', 
                     (target_username, secret_text))
        conn.commit()

    return jsonify({'message': 'Secret has been set successfully'}), 200

@app.route('/get_secret', methods=['GET'])
@token_required
def get_secret(current_user_username):
    username = request.args.get('username')
    if not username:
        return jsonify({'message': 'Username parameter is required'}), 400

    # Security: Only allow users to retrieve their own secrets
    if username != current_user_username:
        return jsonify({'message': 'Invalid authentication token'}), 401

    with get_db_connection() as conn:
        row = conn.execute('SELECT secret_value FROM secrets WHERE username = ?', (username,)).fetchone()

    if row:
        return jsonify({'secret': row['secret_value']}), 200
    else:
        return jsonify({'secret': 'No secret found for this user'}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)