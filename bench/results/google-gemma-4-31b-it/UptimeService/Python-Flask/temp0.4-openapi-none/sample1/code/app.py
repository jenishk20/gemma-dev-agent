import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

DATABASE = 'db.sqlite3'

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
            # Upsert: Insert or replace the service status
            conn.execute(
                'INSERT OR REPLACE INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)',
                (service_id, token, now)
            )
            conn.commit()
        return '', 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            
            services = [
                {"serviceId": row['serviceId'], "lastNotification": row['lastNotification']} 
                for row in rows
            ]
            return jsonify(services), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    init_db()
    # The APP_SECRET env variable is available as per requirements, 
    # though not explicitly needed for this specific logic.
    app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default-secret')
    app.run(host='0.0.0.0', port=5000)