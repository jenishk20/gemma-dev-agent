import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_FILE = "db.sqlite3"

def get_db_connection():
    # Using a fixed filename prevents path traversal
    conn = sqlite3.connect(DB_FILE)
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
        # Fail silently during init or handle as critical
        pass

@app.route('/click', methods=['POST'])
def register_click():
    try:
        # Resource exhaustion: limit request body size if necessary, 
        # though POST /click doesn't read body here.
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Use parameterized query to prevent SQL injection
            # Generate timestamp on server to prevent client-side manipulation
            now = datetime.utcnow().isoformat()
            cursor.execute('INSERT INTO clicks (timestamp) VALUES (?)', (now,))
            conn.commit()
        return jsonify({"message": "Click registered successfully"}), 201
    except Exception:
        # Error handling: return documented 400 and do not leak internal stack traces
        return jsonify({"error": "Invalid request"}), 400

@app.route('/clicks', methods=['GET'])
def retrieve_clicks():
    # Resource exhaustion: limit query parameter length
    date_str = request.args.get('date', '')
    direction = request.args.get('direction', '')

    if not date_str or not direction:
        return jsonify({"error": "Missing required parameters: date and direction"}), 400

    # SQL Injection Prevention: 
    # The 'direction' operator cannot be parameterized in SQLite.
    # We use a strict whitelist (enum) to ensure only safe operators are used.
    allowed_directions = ["<", ">", "<=", ">="]
    if direction not in allowed_directions:
        return jsonify({"error": "Invalid request"}), 400

    # Input Validation: Ensure date is exactly in YYYY-MM-DD format
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid request"}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # The direction is validated against a whitelist, and date_str is parameterized.
            # This prevents SQL injection.
            query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
            cursor.execute(query, (date_str,))
            rows = cursor.fetchall()

            clicks = []
            for row in rows:
                clicks.append({
                    "id": str(row['id']),
                    "timestamp": row['timestamp']
                })

            if not clicks:
                return jsonify({"message": "No clicks found"}), 404

            return jsonify(clicks), 200
    except Exception:
        # Error handling: return documented 400 and do not leak internal details
        return jsonify({"error": "Invalid request"}), 400

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)