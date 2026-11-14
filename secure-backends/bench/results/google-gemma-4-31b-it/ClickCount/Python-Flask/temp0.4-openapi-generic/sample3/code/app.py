import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default-secret-key")

DB_NAME = "db.sqlite3"

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
            # We use CURRENT_TIMESTAMP for the click registration
            cursor = conn.execute('INSERT INTO clicks (timestamp) VALUES (?)', (datetime.utcnow().isoformat(),))
            conn.commit()
            return jsonify({"message": "Click registered successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/clicks', methods=['GET'])
def retrieve_clicks():
    date_str = request.args.get('date')
    direction = request.args.get('direction')

    if not date_str or not direction:
        return jsonify({"error": "Missing required parameters: date and direction"}), 400

    # Validate direction to prevent SQL injection
    allowed_directions = ["<", ">", "<=", ">="]
    if direction not in allowed_directions:
        return jsonify({"error": "Invalid direction. Must be one of <, >, <=, >="}), 400

    # Validate date format (YYYY-MM-DD)
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    try:
        with get_db_connection() as conn:
            # We use a parameterized query for the date, but the operator (direction) 
            # is validated against a whitelist and interpolated safely.
            query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
            rows = conn.execute(query, (date_str,)).fetchall()
            
            clicks = [
                {"id": str(row['id']), "timestamp": row['timestamp']} 
                for row in rows
            ]
            
            if not clicks:
                return jsonify({"error": "No clicks found"}), 404
                
            return jsonify(clicks), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)