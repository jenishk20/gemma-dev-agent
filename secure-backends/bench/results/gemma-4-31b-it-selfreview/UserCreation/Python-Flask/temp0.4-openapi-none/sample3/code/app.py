import os
import sqlite3
import uuid
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key')
# Resource exhaustion: Bound request size to prevent DoS via huge JSON payloads
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB limit

DB_PATH = 'db.sqlite3'

def get_db_connection():
    # Using a context manager for connection ensures it's closed
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Table for invitations
        conn.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
                invite_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        ''')
        # Table for users
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.route('/invite_user', methods=['POST'])
def invite_user():
    try:
        # Use silent=True to avoid crashing on non-JSON content, handle manually
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict) or 'email' not in data:
            return jsonify({"message": "Email is required"}), 400
        
        email = data['email']
        if not isinstance(email, str):
            return jsonify({"message": "Email must be a string"}), 400
        
        with get_db_connection() as conn:
            # SQL Injection Prevention: Using parameterized queries (?)
            cursor = conn.execute('SELECT invite_id FROM invitations WHERE email = ?', (email,))
            row = cursor.fetchone()
            
            if row:
                invite_id = row['invite_id']
            else:
                # Cryptographically secure randomness via uuid4
                invite_id = str(uuid.uuid4())
                conn.execute('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', (invite_id, email))
                conn.commit()
                
            return jsonify({
                "invite_id": invite_id,
                "message": f"Invitation sent to {email}"
            }), 200
    except Exception:
        # Error handling: Generic response to avoid leaking internal stack traces
        return jsonify({"message": "An internal error occurred"}), 500

@app.route('/create_user', methods=['POST'])
def create_user():
    try:
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict):
            return jsonify({"message": "Request body required"}), 400
        
        invite_id = data.get('invite_id')
        user_name = data.get('user_name')
        password = data.get('password')
        
        if not all(isinstance(x, str) for x in [invite_id, user_name, password]):
            return jsonify({"message": "Missing or invalid required fields"}), 400

        with get_db_connection() as conn:
            # SQL Injection Prevention: Parameterized queries
            cursor = conn.execute('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', (invite_id,))
            invite = cursor.fetchone()
            
            if not invite:
                return jsonify({"message": "Invalid invite_id"}), 401
            
            email = invite['email']
            
            # Check if username already exists
            cursor = conn.execute('SELECT id FROM users WHERE user_name = ?', (user_name,))
            if cursor.fetchone():
                return jsonify({"message": "Username already exists. Try providing different username."}), 400
            
            # Secrets: generate_password_hash uses PBKDF2 with a salt by default (strong KDF)
            pw_hash = generate_password_hash(password)
            try:
                conn.execute('INSERT INTO users (user_name, email, password_hash) VALUES (?, ?, ?)', 
                            (user_name, email, pw_hash))
                # Mark invitation as used to prevent reuse (Replay attack prevention)
                conn.execute('UPDATE invitations SET used = 1 WHERE invite_id = ?', (invite_id,))
                conn.commit()
            except sqlite3.IntegrityError:
                return jsonify({"message": "Username or email already registered"}), 400

        return jsonify({"message": "User created successfully"}), 200
    except Exception:
        # Error handling: Generic response to avoid leaking internal stack traces
        return jsonify({"message": "An internal error occurred"}), 500

@app.errorhandler(RequestEntityTooLarge)
def handle_too_large(e):
    return jsonify({"message": "Payload too large"}), 413

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)