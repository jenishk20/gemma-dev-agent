import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
# Use the provided APP_SECRET environment variable
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key_for_dev_only')

DB_NAME = 'db.sqlite3'

def get_db_connection():
    # Use a timeout to prevent resource exhaustion (database locks)
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    except Exception:
        # In a real production app, we would log this, but we must not leak details
        pass

@app.route('/click', methods=['POST'])
def register_click():
    try:
        # Limit request body size to prevent resource exhaustion
        if request.content_length and request.content_length > 1024 * 10: 
            return jsonify({"error": "Request entity too large"}), 400

        with get_db_connection() as conn:
            # Use parameterized query to prevent SQL injection
            # We use utcnow().isoformat() to ensure consistent date-time strings
            timestamp = datetime.utcnow().isoformat()
            conn.execute('INSERT INTO clicks (timestamp) VALUES (?)', (timestamp,))
            conn.commit()
        return jsonify({"message": "Click registered successfully"}), 201
    except Exception:
        # Generic error message to avoid leaking internal database details or stack traces
        return jsonify({"error": "Invalid request"}), 400

@app.route('/clicks', methods=['GET'])
def retrieve_clicks():
    date_str = request.args.get('date')
    direction = request.args.get('direction')

    if not date_str or not direction:
        return jsonify({"error": "Missing required parameters"}), 400

    # Strict validation of the 'direction' operator against an allowed whitelist
    # This prevents SQL injection as the operator cannot be parameterized in SQLite
    allowed_directions = {"<", ">", "<=", ">="}
    if direction not in allowed_directions:
        return jsonify({"error": "Invalid direction"}), 400

    # Strict validation of the date format to ensure it matches YYYY-MM-DD
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid date format"}), 400

    try:
        with get_db_connection() as conn:
            # The 'direction' variable is now guaranteed to be from the whitelist.
            # The 'date_str' is passed as a parameter to the query.
            query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
            cursor = conn.execute(query, (date_str,))
            rows = cursor.fetchall()

            if not rows:
                return jsonify({"message": "No clicks found"}), 404

            clicks = []
            for row in rows:
                clicks.append({
                    "id": str(row['id']),
                    "timestamp": row['timestamp']
                })
            
            return jsonify(clicks), 200
    except Exception:
        # Generic error message to avoid leaking internal database details
        return jsonify({"error": "Invalid request"}), 400

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)