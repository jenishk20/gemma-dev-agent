import os
import sqlite3
import uuid
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash

app = Flask(__name__)
# Use the provided APP_SECRET environment variable
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key_for_dev')

# Limit request size to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

DB_PATH = 'db.sqlite3'

def get_db():
    # Using a context manager for connection to ensure it closes
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
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
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"message": "Invalid JSON"}), 400
        
        email = data.get('email')
        if not email or not isinstance(email, str):
            return jsonify({"message": "Email is required and must be a string"}), 400
        
        # Basic email validation to prevent extremely long strings or weird characters
        if len(email) > 254:
            return jsonify({"message": "Email too long"}), 400

        with get_db() as db:
            # Parameterized query prevents SQL Injection
            cursor = db.execute('SELECT invite_id FROM invitations WHERE email = ?', (email,))
            row = cursor.fetchone()
            
            if row:
                invite_id = row['invite_id']
            else:
                # uuid4 provides cryptographically secure randomness
                invite_id = str(uuid.uuid4())
                db.execute('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', (invite_id, email))
                db.commit()
        
        return jsonify({
            "invite_id": invite_id,
            "message": "Invitation created or retrieved successfully"
        }), 200
    except Exception:
        # Generic error handling to prevent leaking stack traces
        return jsonify({"message": "An internal error occurred"}), 500

@app.route('/create_user', methods=['POST'])
def create_user():
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"message": "Invalid JSON"}), 400
        
        invite_id = data.get('invite_id')
        user_name = data.get('user_name')
        password = data.get('password')
        
        if not all(isinstance(x, str) for x in [invite_id, user_name, password]):
            return jsonify({"message": "invite_id, user_name, and password are required and must be strings"}), 400
        
        # Prevent resource exhaustion from extremely long inputs
        if len(user_name) > 100 or len(password) > 128 or len(invite_id) > 100:
            return jsonify({"message": "Input length exceeds limit"}), 400

        with get_db() as db:
            # Parameterized query prevents SQL Injection
            cursor = db.execute('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', (invite_id,))
            invite = cursor.fetchone()
            
            if not invite:
                return jsonify({"message": "Invalid invite_id"}), 401
            
            email = invite['email']
            
            # Check if username already exists
            cursor = db.execute('SELECT 1 FROM users WHERE user_name = ?', (user_name,))
            if cursor.fetchone():
                return jsonify({"message": "Username already exists. Try providing different username."}), 400

            # Werkzeug's generate_password_hash uses a strong salted KDF (scrypt or pbkdf2:sha256)
            pw_hash = generate_password_hash(password)
            
            try:
                db.execute('INSERT INTO users (user_name, email, password_hash) VALUES (?, ?, ?)', 
                           (user_name, email, pw_hash))
                # Mark invitation as used to prevent reuse (Replay Attack)
                db.execute('UPDATE invitations SET used = 1 WHERE invite_id = ?', (invite_id,))
                db.commit()
            except sqlite3.IntegrityError:
                return jsonify({"message": "Username or Email already exists"}), 400
        
        return jsonify({"message": "User created successfully"}), 200
    except Exception:
        # Generic error handling to prevent leaking stack traces
        return jsonify({"message": "An internal error occurred"}), 500

if __name__ == '__main__':
    init_db()
    # Running on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)