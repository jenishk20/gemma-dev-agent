import os
import sqlite3
import uuid
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_for_dev')
DATABASE = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Invitations table: stores email and a unique invite_id
        conn.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                invite_id TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        ''')
        # Users table: stores username, hashed password, and email
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        ''')
        conn.commit()

@app.route('/invite_user', methods=['POST'])
def invite_user():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"message": "Email is required"}), 400

    email = data['email']
    
    with get_db_connection() as conn:
        # Check if invitation already exists for this email
        cur = conn.execute('SELECT invite_id FROM invitations WHERE email = ?', (email,))
        row = cur.fetchone()
        
        if row:
            invite_id = row['invite_id']
        else:
            # Create a new unique invitation ID
            invite_id = str(uuid.uuid4())
            conn.execute('INSERT INTO invitations (email, invite_id) VALUES (?, ?)', (email, invite_id))
            conn.commit()

    return jsonify({
        "invite_id": invite_id,
        "message": f"Invitation created for {email}"
    }), 200

@app.route('/create_user', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body required"}), 400

    invite_id = data.get('invite_id')
    user_name = data.get('user_name')
    password = data.get('password')

    if not all([invite_id, user_name, password]):
        return jsonify({"message": "invite_id, user_name, and password are required"}), 400

    with get_db_connection() as conn:
        # Validate invitation
        cur = conn.execute('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', (invite_id,))
        invite = cur.fetchone()
        
        if not invite:
            return jsonify({"message": "Invalid invite_id"}), 401

        email = invite['email']

        # Check if username already exists
        cur = conn.execute('SELECT id FROM users WHERE username = ?', (user_name,))
        if cur.fetchone():
            return jsonify({"message": "Username already exists. Try providing different username."}), 400

        # Hash password and create user
        pw_hash = generate_password_hash(password)
        try:
            conn.execute('INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)', 
                        (user_name, pw_hash, email))
            # Mark invitation as used
            conn.execute('UPDATE invitations SET used = 1 WHERE invite_id = ?', (invite_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            return jsonify({"message": "Username or email already registered"}), 400

    return jsonify({"message": "User created successfully"}), 200

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)