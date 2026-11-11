import os
import sqlite3
import uuid
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash

app = Flask(__name__)
# Use the provided APP_SECRET env variable for the secret key
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key')

DB_NAME = 'db.sqlite3'

def get_db_connection():
    # Using a context manager for the connection ensures it is closed
    conn = sqlite3.connect(DB_NAME)
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
                password TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.route('/invite_user', methods=['POST'])
def invite_user():
    # Resource exhaustion: Limit request body size to prevent DoS
    if request.content_length and request.content_length > 1024 * 10: # 10KB limit
        return jsonify({"message": "Request body too large"}), 400

    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict) or 'email' not in data:
        return jsonify({"message": "Email is required"}), 400
    
    email = data['email']
    if not isinstance(email, str):
        return jsonify({"message": "Email must be a string"}), 400
    
    try:
        with get_db_connection() as conn:
            # SQL Injection prevention: using parameterized queries
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
                "message": "Invitation successfully retrieved or created."
            }), 200
    except Exception:
        # Error handling: Return generic error to avoid leaking internal details/stack traces
        return jsonify({"message": "An internal error occurred"}), 500

@app.route('/create_user', methods=['POST'])
def create_user():
    # Resource exhaustion: Limit request body size
    if request.content_length and request.content_length > 1024 * 10:
        return jsonify({"message": "Request body too large"}), 400

    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"message": "Invalid request body"}), 400
    
    invite_id = data.get('invite_id')
    user_name = data.get('user_name')
    password = data.get('password')
    
    if not all([invite_id, user_name, password]):
        return jsonify({"message": "Missing required fields"}), 400

    if not all(isinstance(x, str) for x in [invite_id, user_name, password]):
        return jsonify({"message": "All fields must be strings"}), 400

    try:
        with get_db_connection() as conn:
            # SQL Injection prevention: using parameterized queries
            cursor = conn.execute('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', (invite_id,))
            inv_row = cursor.fetchone()
            
            if not inv_row:
                # 401 Unauthorized as per OpenAPI spec for invalid invite_id
                return jsonify({"message": "Invalid invite_id"}), 401
            
            email = inv_row['email']
            
            # Check if username already exists
            cursor = conn.execute('SELECT 1 FROM users WHERE user_name = ?', (user_name,))
            if cursor.fetchone():
                return jsonify({"message": "Username already exists. Try providing different username."}), 400
            
            # Secrets: Using Werkzeug's generate_password_hash which uses PBKDF2 with a salt
            hashed_pw = generate_password_hash(password)
            conn.execute('INSERT INTO users (user_name, email, password) VALUES (?, ?, ?)', 
                         (user_name, email, hashed_pw))
            
            # Mark invitation as used to prevent reuse (replay attack)
            conn.execute('UPDATE invitations SET used = 1 WHERE invite_id = ?', (invite_id,))
            conn.commit()
            
            return jsonify({"message": "User created successfully"}), 200
            
    except Exception:
        # Error handling: Return generic error to avoid leaking internal details
        return jsonify({"message": "An internal error occurred"}), 500

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)