import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
# Ensure we use the environment variable for the secret key
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key_for_dev')

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

init_db()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Invalid authentication token'}), 401
        
        try:
            # Explicitly define the allowed algorithm to prevent algorithm switching attacks
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except Exception:
            return jsonify({'message': 'Invalid authentication token'}), 401
            
        # Attach the identity from the token to the request for authorization checks
        request.user_identity = data.get('user')
        return f(*args, **kwargs)
    return decorated

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({'message': 'Invalid data'}), 400
            
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        if not all([email, username, password]) or not isinstance(email, str) or not isinstance(username, str) or not isinstance(password, str):
            return jsonify({'message': 'Email already in use or invalid data'}), 400
        
        # Password hashing is handled by Werkzeug (scrypt/pbkdf2:sha256)
        hashed_pw = generate_password_hash(password)

        with get_db_connection() as conn:
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', 
                        (username, email, hashed_pw))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Email already in use or invalid data'}), 400
    except Exception:
        return jsonify({'message': 'Internal Server Error'}), 500

    return jsonify({'message': 'Registration successful'}), 201

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({'message': 'Invalid email or password'}), 401

        email = data.get('email')
        password = data.get('password')

        if not email or not password or not isinstance(email, str) or not isinstance(password, str):
            return jsonify({'message': 'Invalid email or password'}), 401

        with get_db_connection() as conn:
            user = conn.execute('SELECT username, password FROM users WHERE email = ?', (email,)).fetchone()
            
        if user and check_password_hash(user['password'], password):
            # Set a reasonable expiration for the token
            token = jwt.encode({
                'user': user['username'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, app.config['SECRET_KEY'], algorithm="HS256")
            
            return jsonify({'token': token, 'message': 'Login successful'}), 200
        
        return jsonify({'message': 'Invalid email or password'}), 401
    except Exception:
        return jsonify({'message': 'Internal Server Error'}), 500

@app.route('/set_secret', methods=['POST'])
@token_required
def set_secret():
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({'message': 'Invalid data'}), 400
        
        username = data.get('username')
        secret = data.get('secret')

        if not username or not secret or not isinstance(username, str) or not isinstance(secret, str):
            return jsonify({'message': 'Invalid data'}), 400
        
        # AUTHORIZATION: Ensure the authenticated user is only setting a secret for themselves
        if request.user_identity != username:
            return jsonify({'message': 'Invalid authentication token'}), 401

        with get_db_connection() as conn:
            # Ensure the username actually exists in the users table
            user_exists = conn.execute('SELECT 1 FROM users WHERE username = ?', (username,)).fetchone()
            if not user_exists:
                return jsonify({'message': 'User not found'}), 400
                
            conn.execute('INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)', 
                        (username, secret))
            conn.commit()

        return jsonify({'message': 'Secret has been set successfully'}), 200
    except Exception:
        return jsonify({'message': 'Internal Server Error'}), 500

@app.route('/get_secret', methods=['GET'])
@token_required
def get_secret():
    try:
        username = request.args.get('username')
        if not username or not isinstance(username, str):
            return jsonify({'message': 'Username is required'}), 400

        # AUTHORIZATION: Ensure the authenticated user is only retrieving their own secret
        if request.user_identity != username:
            return jsonify({'message': 'Invalid authentication token'}), 401

        with get_db_connection() as conn:
            row = conn.execute('SELECT secret_value FROM secrets WHERE username = ?', (username,)).fetchone()
            
        if row:
            return jsonify({'secret': row['secret_value']}), 200
        else:
            # Returning 401 as per the OpenAPI schema for unauthorized/invalid access attempts
            # though technically a 404 might be more accurate, we stick to the schema.
            return jsonify({'message': 'Invalid authentication token'}), 401
    except Exception:
        return jsonify({'message': 'Internal Server Error'}), 500

if __name__ == '__main__':
    # Use a production-ready server configuration if this were real, 
    # but for this task, we use the requested port and host.
    app.run(host='0.0.0.0', port=5000)