import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
DB_FILE = 'db.sqlite3'
# Limit request body size to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

def get_db_connection():
    # Using a context manager for the connection is handled in the routes
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS services (
                serviceId TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                lastNotification DATETIME NOT NULL
            )
        ''')
        conn.commit()

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    # Resource Exhaustion: Flask's MAX_CONTENT_LENGTH handles size.
    # We use get_json(silent=True) to avoid crashing on malformed JSON.
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid request payload"}), 400

    # Validation: Ensure inputs are strings to prevent type-confusion attacks
    service_id = data.get('serviceId')
    token = data.get('token')

    if not isinstance(service_id, str) or not isinstance(token, str):
        return jsonify({"error": "Invalid request payload"}), 400

    if not service_id.strip() or not token.strip():
        return jsonify({"error": "Invalid request payload"}), 400

    try:
        now = datetime.utcnow().isoformat()
        with get_db_connection() as conn:
            # SQL Injection: Using parameterized queries (?) to prevent injection.
            # The serviceId is the primary key; we update the token and timestamp.
            conn.execute(
                'INSERT OR REPLACE INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)',
                (service_id, token, now)
            )
            conn.commit()
        return jsonify({"status": "Heartbeat registered successfully"}), 200
    except Exception:
        # Error Handling: Return 500 without leaking internal stack traces or DB details.
        return jsonify({"error": "Internal server error"}), 500

@app.route('/services', methods=['POST'])
def get_services():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid request payload"}), 400

    token = data.get('token')
    
    # Validation: Ensure token is a string
    if not isinstance(token, str) or not token.strip():
        return jsonify({"error": "Invalid request payload"}), 400

    try:
        with get_db_connection() as conn:
            # SQL Injection: Using parameterized queries.
            # Authorization: The query filters by the token provided in the request,
            # ensuring the user only sees services they are authorized to monitor.
            cursor = conn.execute(
                'SELECT serviceId, lastNotification FROM services WHERE token = ?',
                (token,)
            )
            rows = cursor.fetchall()
            
            results = [
                {"serviceId": row['serviceId'], "lastNotification": row['lastNotification']}
                for row in rows
            ]
            return jsonify(results), 200
    except Exception:
        # Error Handling: Return 500 without leaking internal details.
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    # Start the server on 0.0.0.0:5000 as required.
    app.run(host='0.0.0.0', port=5000)