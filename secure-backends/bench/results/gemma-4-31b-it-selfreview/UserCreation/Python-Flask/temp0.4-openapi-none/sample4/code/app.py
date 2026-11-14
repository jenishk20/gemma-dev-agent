import os
import sqlite3
import uuid
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key')
# Resource exhaustion: Limit request body size to 1MB to prevent DoS
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

DB_NAME = 'db.sqlite3'

def get_db_connection():
    # Use a connection that doesn't allow multiple statements to mitigate potential SQLi
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
                email TEXT PRIMARY KEY,
                invite_id TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.route('/invite_user', methods=['POST'])
def invite_user():
    try:
        # Resource exhaustion/Input validation: Ensure JSON is present and not too large
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"message": "Invalid JSON"}), 400
        
        email = data.get('email')
        if not email or not isinstance(email, str):
            return jsonify({"message": "Email is required and must be a string"}), 400
        
        # Basic email length check to prevent resource exhaustion in DB
        if len(email) > 254:
            return jsonify({"message": "Email too long"}), 400

        with get_db_connection() as conn:
            # SQL Injection prevention: Use parameterized queries
            row = conn.execute('SELECT invite_id FROM invitations WHERE email = ?', (email,)).fetchone()
            
            if row:
                invite_id = row['invite_id']
            else:
                # Cryptographically secure randomness: uuid4 uses os.urandom
                invite_id = str(uuid.uuid4())
                conn.execute('INSERT INTO invitations (email, invite_id) VALUES (?, ?)', (email, invite_id))
                conn.commit()
                
        return jsonify({
            "invite_id": invite_id,
            "message": f"Invitation created for {email}"
        }), 200
    except Exception:
        # Error handling: Catch all to prevent leaking stack traces
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
        
        # Input validation: Ensure all fields are present and are strings
        if not all(isinstance(x, str) for x in [invite_id, user_name, password]):
            return jsonify({"message": "Missing or invalid required fields"}), 400

        # Resource exhaustion: Limit length of inputs
        if len(user_name) > 100 or len(password) > 128 or len(invite_id) > 64:
            return jsonify({"message": "Input fields too long"}), 400

        with get_db_connection() as conn:
            # SQL Injection prevention: Parameterized query
            invitation = conn.execute(
                'SELECT email FROM invitations WHERE invite_id = ? AND used = 0', 
                (invite_id,)
            ).fetchone()
            
            if not invitation:
                return jsonify({"message": "Invalid invite_id"}), 401
            
            email = invitation['email']
            
            # SQL Injection prevention: Parameterized query
            existing_user = conn.execute('SELECT id FROM users WHERE username = ?', (user_name,)).fetchone()
            if existing_user:
                return jsonify({"message": "Username already exists. Try providing different username."}), 400
            
            # Secrets: generate_password_hash uses PBKDF2 with a salt by default (strong KDF)
            hashed_pw = generate_password_hash(password)
            
            try:
                conn.execute(
                    'INSERT INTO users (username, password, email) VALUES (?, ?, ?)', 
                    (user_name, hashed_pw, email)
                )
                conn.execute('UPDATE invitations SET used = 1 WHERE invite_id = ?', (invite_id,))
                conn.commit()
            except sqlite3.IntegrityError:
                return jsonify({"message": "Username already exists."}), 400

        return jsonify({"message": "User created successfully"}), 200
    except Exception:
        # Error handling: Catch all to prevent leaking stack traces
        return jsonify({"message": "An internal error occurred"}), 500

# Handle request size limit globally
@app.errorhandler(RequestEntityTooLarge)
def handle_too_large(e):
    return jsonify({"message": "Request body too large"}), 413

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)