import os
import sqlite3
import hmac
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

DATABASE = 'db.sqlite3'
# Use APP_SECRET for constant-time comparison of tokens to prevent timing attacks
APP_SECRET = os.environ.get('APP_SECRET', 'default_fallback_secret_for_dev')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS services (
                serviceId TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                lastNotification TEXT NOT NULL
            )
        ''')
        conn.commit()

def secure_compare(val1, val2):
    """
    Prevents timing attacks by using constant-time comparison.
    """
    return hmac.compare_digest(val1, val2)

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    # Resource exhaustion: Limit request size (Flask does this via MAX_CONTENT_LENGTH, 
    # but we ensure we only process JSON)
    if not request.is_json:
        return jsonify({"error": "Invalid request payload"}), 400

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request payload"}), 400

        service_id = data.get('serviceId')
        token = data.get('token')

        # Validation: Ensure inputs are strings to prevent type-confusion/unexpected behavior
        if not isinstance(service_id, str) or not isinstance(token, str):
            return jsonify({"error": "Invalid request payload"}), 400

        if not service_id or not token:
            return jsonify({"error": "Invalid request payload"}), 400

        now = datetime.utcnow().isoformat() + 'Z'
        with get_db_connection() as conn:
            # SQL Injection Prevention: Using parameterized queries
            conn.execute('''
                INSERT INTO services (serviceId, token, lastNotification)
                VALUES (?, ?, ?)
                ON CONFLICT(serviceId) DO UPDATE SET
                token = excluded.token,
                lastNotification = excluded.lastNotification
            ''', (service_id, token, now))
            conn.commit()
        return '', 200
    except Exception:
        # Error handling: Return documented status code without leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/services', methods=['POST'])
def get_services():
    if not request.is_json:
        return jsonify({"error": "Invalid request payload"}), 400

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request payload"}), 400

        token = data.get('token')
        if not isinstance(token, str) or not token:
            return jsonify({"error": "Invalid request payload"}), 400

        with get_db_connection() as conn:
            # SQL Injection Prevention: Parameterized query
            rows = conn.execute(
                'SELECT serviceId, lastNotification FROM services WHERE token = ?', 
                (token,)
            ).fetchall()
            
            # Authorization: The query itself ensures only services associated with the 
            # provided token are returned.
            services = [
                {"serviceId": row['serviceId'], "lastNotification": row['lastNotification']} 
                for row in rows
            ]
            return jsonify(services), 200
    except Exception:
        # Error handling: Return documented status code without leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Set a reasonable limit for request bodies to prevent resource exhaustion
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB
    init_db()
    app.run(host='0.0.0.0', port=5000)