import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
# Use the provided APP_SECRET env variable
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default-secret-key')

DB_NAME = 'db.sqlite3'

def get_db_connection():
    # Using a context manager for the connection is handled in the routes
    conn = sqlite3.connect(DB_NAME)
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
        # Limit request body size to prevent resource exhaustion (DoS)
        if request.content_length and request.content_length > 1024:
            return jsonify({"error": "Request body too large"}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Use parameterized query (though no user input is used here, it's best practice)
            cursor.execute('INSERT INTO clicks (timestamp) VALUES (CURRENT_TIMESTAMP)')
            conn.commit()
            return jsonify({"message": "Click registered successfully"}), 201
    except Exception:
        # Generic error message to avoid leaking internal database details/stack traces
        return jsonify({"error": "An internal error occurred"}), 400

@app.route('/clicks', methods=['GET'])
def retrieve_clicks():
    # Extract parameters
    date_str = request.args.get('date')
    direction = request.args.get('direction')

    # Validation for required parameters
    if not date_str or not direction:
        return jsonify({"error": "Missing required parameters 'date' and 'direction'"}), 400

    # Strict validation of the 'direction' operator to prevent SQL Injection.
    # Since operators cannot be parameterized in SQL, we use a strict allow-list.
    allowed_directions = ["<", ">", "<=", ">="]
    if direction not in allowed_directions:
        return jsonify({"error": "Invalid direction. Must be one of <, >, <=, >="}), 400

    # Validate date format (YYYY-MM-DD) to ensure it's a valid date and prevent injection
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    try:
        with get_db_connection() as conn:
            # The 'direction' is verified against a strict allow-list.
            # The 'date_str' is passed as a parameter to the sqlite3 API to prevent SQL injection.
            query = f"SELECT id, timestamp FROM clicks WHERE date(timestamp) {direction} ?"
            clicks_data = conn.execute(query, (date_str,)).fetchall()
            
            if not clicks_data:
                return jsonify({"error": "No clicks found"}), 404

            results = []
            for row in clicks_data:
                results.append({
                    "id": str(row['id']),
                    "timestamp": row['timestamp']
                })
            
            return jsonify(results), 200
    except Exception:
        # Return documented error status code without leaking internal details
        return jsonify({"error": "An internal error occurred"}), 400

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)