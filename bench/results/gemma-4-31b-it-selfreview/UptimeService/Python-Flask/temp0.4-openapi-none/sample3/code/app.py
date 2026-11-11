import os
import sqlite3
import hmac
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
DB_PATH = 'db.sqlite3'
# Use APP_SECRET for HMAC-based token storage if available, otherwise a fallback
SECRET_KEY = os.environ.get('APP_SECRET', 'default_secret_for_dev_only')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS services (
                serviceId TEXT PRIMARY KEY,
                token_hash TEXT NOT NULL,
                lastNotification DATETIME NOT NULL
            )
        ''')
        conn.commit()

def hash_token(token: str) -> str:
    """
    Store tokens using HMAC-SHA256 to prevent plaintext token leakage 
    from the database and ensure constant-time comparison.
    """
    return hmac.new(SECRET_KEY.encode(), token.encode(), 'sha256').hexdigest()

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    # Resource exhaustion: Limit request body size (Flask default is usually 16MB, 
    # but we ensure we are handling JSON safely)
    if request.content_length > 10 * 1024: # 10KB limit for heartbeats
        return jsonify({"error": "Request body too large"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid request payload"}), 400

    service_id = data.get('serviceId')
    token = data.get('token')

    # Validate input types and presence
    if not isinstance(service_id, str) or not isinstance(token, str):
        return jsonify({"error": "Invalid request payload"}), 400

    if not service_id or not token:
        return jsonify({"error": "Invalid request payload"}), 400

    try:
        # Use UTC for consistency
        now = datetime.utcnow().isoformat()
        token_hash = hash_token(token)
        
        with get_db_connection() as conn:
            # Parameterized query prevents SQL Injection
            conn.execute(
                'INSERT INTO services (serviceId, token_hash, lastNotification) VALUES (?, ?, ?) '
                'ON CONFLICT(serviceId) DO UPDATE SET token_hash=excluded.token_hash, lastNotification=excluded.lastNotification',
                (service_id, token_hash, now)
            )
            conn.commit()
        return jsonify({"status": "Heartbeat registered successfully"}), 200
    except Exception:
        # Error handling: Do not leak stack traces or internal DB errors
        return jsonify({"error": "Internal server error"}), 500

@app.route('/services', methods=['POST'])
def get_services():
    if request.content_length > 10 * 1024:
        return jsonify({"error": "Request body too large"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid request payload"}), 400

    token = data.get('token')
    if not isinstance(token, str) or not token:
        return jsonify({"error": "Invalid request payload"}), 400

    try:
        token_hash = hash_token(token)
        with get_db_connection() as conn:
            # Parameterized query prevents SQL Injection
            cursor = conn.execute(
                'SELECT serviceId, lastNotification FROM services WHERE token_hash = ?', 
                (token_hash,)
            )
            rows = cursor.fetchall()
            
            results = [
                {"serviceId": row['serviceId'], "lastNotification": row['lastNotification']} 
                for row in rows
            ]
            return jsonify(results), 200
    except Exception:
        # Error handling: Do not leak internal details
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    # Port 5000, Host 0.0.0.0 as requested
    app.run(host='0.0.0.0', port=5000)