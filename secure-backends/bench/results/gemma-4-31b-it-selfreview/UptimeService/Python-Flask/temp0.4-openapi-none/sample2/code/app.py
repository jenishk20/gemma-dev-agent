import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
# Secret key is used by Flask for session signing, though not used in this specific API
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default-secret-key')

# Hardcoded DB path to prevent path traversal
DB_PATH = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
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
    # Resource exhaustion: Limit request body size (Flask does this via MAX_CONTENT_LENGTH, 
    # but we can also check if JSON is too large)
    try:
        # Use silent=True to avoid crashing on non-JSON payloads
        data = request.get_json(silent=True)
    except Exception:
        return jsonify({"error": "Invalid request payload"}), 400

    if data is None:
        return jsonify({"error": "Invalid request payload"}), 400
    
    # Input validation: Ensure we only process expected keys and types
    service_id = data.get('serviceId')
    token = data.get('token')
    
    if not isinstance(service_id, str) or not isinstance(token, str):
        return jsonify({"error": "Invalid request payload"}), 400
    
    if not service_id or not token:
        return jsonify({"error": "Invalid request payload"}), 400
    
    try:
        # Use UTC ISO format for consistent date-time representation
        now = datetime.utcnow().isoformat()
        with get_db_connection() as conn:
            # SQL Injection prevention: Using parameterized queries (?)
            # This ensures untrusted input is treated as data, not code.
            conn.execute(
                'INSERT OR REPLACE INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)',
                (service_id, token, now)
            )
            conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception:
        # Error handling: Generic 500 response without leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/services', methods=['POST'])
def get_services():
    try:
        data = request.get_json(silent=True)
    except Exception:
        return jsonify({"error": "Invalid request payload"}), 400

    if data is None:
        return jsonify({"error": "Invalid request payload"}), 400
    
    token = data.get('token')
    if not isinstance(token, str) or not token:
        return jsonify({"error": "Invalid request payload"}), 400
    
    try:
        with get_db_connection() as conn:
            # SQL Injection prevention: Using parameterized queries (?)
            # Authorization: Only services matching the provided token are returned.
            cursor = conn.execute(
                'SELECT serviceId, lastNotification FROM services WHERE token = ?',
                (token,)
            )
            rows = cursor.fetchall()
            
            # Ensure we only return the specific fields defined in the OpenAPI schema
            services_list = [
                {"serviceId": row['serviceId'], "lastNotification": row['lastNotification']} 
                for row in rows
            ]
            
        return jsonify(services_list), 200
    except Exception:
        # Error handling: Generic 500 response without leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)