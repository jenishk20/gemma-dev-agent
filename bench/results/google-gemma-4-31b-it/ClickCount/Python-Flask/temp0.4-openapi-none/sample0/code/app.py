import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key')

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
            # We use current timestamp for the click registration
            cursor.execute('INSERT INTO clicks (timestamp) VALUES (?)', (datetime.utcnow().isoformat(),))
            conn.commit()
            return jsonify({"message": "Click registered successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/clicks', methods=['GET'])
def retrieve_clicks():
    date_str = request.args.get('date')
    direction = request.args.get('direction')

    if not date_str or not direction:
        return jsonify({"error": "Missing required query parameters: date and direction"}), 400

    if direction not in ["<", ">", "<=", ">="]:
        return jsonify({"error": "Invalid direction. Must be one of: <, >, <=, >="}), 400

    try:
        # Validate date format (YYYY-MM-DD)
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Use a parameterized query for the date, but the operator must be hardcoded/validated
            # since SQL parameters cannot be used for operators.
            query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
            cursor.execute(query, (date_str,))
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
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)