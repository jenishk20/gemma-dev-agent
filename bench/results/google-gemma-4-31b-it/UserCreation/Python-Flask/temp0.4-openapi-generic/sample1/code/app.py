import os
import sqlite3
import uuid
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default-secret-key-for-dev')

DB_NAME = 'db.sqlite3'

def get_db():
    """Connects to the SQLite database and returns the connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema."""
    with get_db() as conn:
        # Invitations table: stores the email and a unique invite_id
        conn.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
                invite_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        ''')
        # Users table: stores user credentials
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT
            )
        ''')
        conn.commit()

@app.route('/invite_user', methods=['POST'])
def invite_user():
    """
    Creates an invitation for a specific email. 
    If the email already has an invitation, returns the existing ID.
    """
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"message": "Email is required"}), 400
    
    email = data['email']
    
    with get_db() as conn:
        # Check if invitation already exists for this email
        cursor = conn.execute('SELECT invite_id FROM invitations WHERE email = ?', (email,))
        row = cursor.fetchone()
        
        if row:
            invite_id = row['invite_id']
        else:
            # Create a new unique invite_id
            invite_id = str(uuid.uuid4())
            conn.execute('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', (invite_id, email))
            conn.commit()
            
    return jsonify({
        "invite_id": invite_id,
        "message": "Invitation created successfully"
    }), 200

@app.route('/create_user', methods=['POST'])
def create_user():
    """
    Creates a user account using a valid and unused invitation ID.
    """
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body is required"}), 400
    
    invite_id = data.get('invite_id')
    user_name = data.get('user_name')
    password = data.get('password')
    
    if not all([invite_id, user_name, password]):
        return jsonify({"message": "invite_id, user_name, and password are required"}), 400

    with get_db() as conn:
        # 1. Validate invitation
        cursor = conn.execute('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', (invite_id,))
        invite = cursor.fetchone()
        
        if not invite:
            return jsonify({"message": "Invalid invite_id"}), 401
        
        email = invite['email']
        
        # 2. Check if username already exists
        cursor = conn.execute('SELECT id FROM users WHERE user_name = ?', (user_name,))
        if cursor.fetchone():
            return jsonify({"message": "Username already exists. Try providing different username."}), 400
        
        # 3. Create user with hashed password
        hashed_pw = generate_password_hash(password)
        try:
            conn.execute('INSERT INTO users (user_name, password, email) VALUES (?, ?, ?)', 
                         (user_name, hashed_pw, email))
            # 4. Mark invitation as used
            conn.execute('UPDATE invitations SET used = 1 WHERE invite_id = ?', (invite_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            return jsonify({"message": "Username already exists."}), 400

    return jsonify({"message": "User created successfully"}), 200

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)