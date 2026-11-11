import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key')

# Limit request body size to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

DB_NAME = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

@app.route('/click', methods=['POST'])
def register_click():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Use UTC timestamp to ensure consistency and avoid timezone-based injection/errors
            timestamp = datetime.utcnow().isoformat()
            cursor.execute('INSERT INTO clicks (timestamp) VALUES (?)', (timestamp,))
            conn.commit()
            return jsonify({"message": "Click registered successfully"}), 201
    except Exception:
        # Generic error to avoid leaking internal database details/stack traces
        return jsonify({"error": "Invalid request"}), 400

@app.route('/clicks', methods=['GET'])
def retrieve_clicks():
    date_str = request.args.get('date')
    direction = request.args.get('direction')

    if not date_str or not direction:
        return jsonify({"error": "Missing required parameters: date and direction"}), 400

    # Strict whitelist for the operator to prevent SQL injection via the operator field
    # since operators cannot be parameterized in SQLite.
    allowed_directions = {"<", ">", "<=", ">="}
    if direction not in allowed_directions:
        return jsonify({"error": "Invalid request"}), 400

    try:
        # Validate date format strictly (YYYY-MM-DD) to prevent injection or malformed data
        datetime.strptime(date_str, '%Y-%m-%d')
        
        with get_db_connection() as conn:
            # The 'direction' is safe because it is checked against a strict whitelist.
            # The 'date_str' is passed as a parameter to prevent SQL injection.
            query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
            cursor = conn.execute(query, (date_str,))
            rows = cursor.fetchall()

            if not rows:
                return jsonify({"error": "No clicks found"}), 404

            clicks = []
            for row in rows:
                clicks.append({
                    "id": str(row['id']),
                    "timestamp": row['timestamp']
                })
            
            return jsonify(clicks), 200
    except ValueError:
        # Invalid date format
        return jsonify({"error": "Invalid request"}), 400
    except Exception:
        # Generic error to avoid leaking internal details
        return jsonify({"error": "Invalid request"}), 400

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)