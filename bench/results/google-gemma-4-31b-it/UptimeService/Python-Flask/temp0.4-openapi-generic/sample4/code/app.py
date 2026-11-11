import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default-secret-key")

DB_FILE = "db.sqlite3"

def get_db_connection():
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
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request payload"}), 400

    service_id = data.get('serviceId')
    token = data.get('token')

    if not service_id or not token:
        return jsonify({"error": "Missing serviceId or token"}), 400

    try:
        now = datetime.utcnow().isoformat()
        with get_db_connection() as conn:
            # Use UPSERT logic to update existing service or insert new one
            conn.execute('''
                INSERT INTO services (serviceId, token, lastNotification)
                VALUES (?, ?, ?)
                ON CONFLICT(serviceId) DO UPDATE SET
                    token = excluded.token,
                    lastNotification = excluded.lastNotification
            ''', (service_id, token, now))
            conn.commit()
        return jsonify({"status": "Heartbeat registered successfully"}), 200
    except Exception as e:
        app.logger.error(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/services', methods=['POST'])
def get_services():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request payload"}), 400

    token = data.get('token')
    if not token:
        return jsonify({"error": "Missing token"}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                'SELECT serviceId, lastNotification FROM services WHERE token = ?', 
                (token,)
            )
            rows = cursor.fetchall()
            
            services_list = [
                {"serviceId": row['serviceId'], "lastNotification": row['lastNotification']} 
                for row in rows
            ]
            
        return jsonify(services_list), 200
    except Exception as e:
        app.logger.error(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)