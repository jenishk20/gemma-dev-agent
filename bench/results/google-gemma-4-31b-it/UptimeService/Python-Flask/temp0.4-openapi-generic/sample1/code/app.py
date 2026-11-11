import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
# The APP_SECRET is provided via env variable as requested, though not strictly 
# needed for this specific logic since we use tokens provided in the request body.
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default-secret-key')

DB_NAME = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS services (
                serviceId TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                lastNotification DATETIME DEFAULT CURRENT_TIMESTAMP
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
        return jsonify({"error": "serviceId and token are required"}), 400
    
    try:
        with get_db_connection() as conn:
            # Use UPSERT logic to update the heartbeat or insert the service if it doesn't exist
            # We check the token during update to ensure only the owner can update the heartbeat
            cursor = conn.execute(
                'SELECT token FROM services WHERE serviceId = ?', (service_id,)
            )
            row = cursor.fetchone()
            
            if row:
                # Service exists, verify token
                if row['token'] != token:
                    return jsonify({"error": "Unauthorized"}), 403
                
                conn.execute(
                    'UPDATE services SET lastNotification = ?, token = ? WHERE serviceId = ?',
                    (datetime.utcnow().isoformat(), token, service_id)
                )
            else:
                # New service registration
                conn.execute(
                    'INSERT INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)',
                    (service_id, token, datetime.utcnow().isoformat())
                )
            conn.commit()
            
        return jsonify({"status": "Heartbeat registered successfully"}), 200
    except Exception as e:
        app.logger.error(f"Internal server error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/services', methods=['POST'])
def get_services():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Invalid request payload"}), 400
    
    token = data.get('token')
    if not token:
        return jsonify({"error": "token is required"}), 400
    
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
        app.logger.error(f"Internal server error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)