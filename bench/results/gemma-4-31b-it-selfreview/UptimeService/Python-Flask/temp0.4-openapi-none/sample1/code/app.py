import os
import sqlite3
import hmac
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

DATABASE = 'db.sqlite3'

# Use a fixed-size limit for request bodies to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

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

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    # Ensure request is JSON
    if not request.is_json:
        return jsonify({"error": "Invalid request payload"}), 400
        
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid request payload"}), 400

    service_id = data.get('serviceId')
    token = data.get('token')

    # Validate input types and presence
    if not isinstance(service_id, str) or not isinstance(token, str):
        return jsonify({"error": "Invalid request payload"}), 400

    try:
        now = datetime.utcnow().isoformat()
        with get_db_connection() as conn:
            # Use parameterized query to prevent SQL Injection
            conn.execute(
                'INSERT OR REPLACE INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)',
                (service_id, token, now)
            )
            conn.commit()
        return '', 200
    except Exception:
        # Generic error to prevent leaking internal database details or stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/services', methods=['POST'])
def get_services():
    # Ensure request is JSON
    if not request.is_json:
        return jsonify({"error": "Invalid request payload"}), 400

    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid request payload"}), 400

    token = data.get('token')
    if not isinstance(token, str):
        return jsonify({"error": "Invalid request payload"}), 400

    try:
        with get_db_connection() as conn:
            # Use parameterized query to prevent SQL Injection
            cursor = conn.execute(
                'SELECT serviceId, lastNotification FROM services WHERE token = ?',
                (token,)
            )
            rows = cursor.fetchall()
            
            # Map results to the required schema
            services = [
                {"serviceId": row['serviceId'], "lastNotification": row['lastNotification']} 
                for row in rows
            ]
            return jsonify(services), 200
    except Exception:
        # Generic error to prevent leaking internal database details or stack traces
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    # Use APP_SECRET for Flask session/signing if needed, though not used in current logic
    app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default-secret-key-change-me')
    app.run(host='0.0.0.0', port=5000)