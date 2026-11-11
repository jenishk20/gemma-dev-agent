import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret')

# Resource Exhaustion: Limit request body size to prevent memory exhaustion
# 1MB is plenty for the specified JSON payloads
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

DB_NAME = 'db.sqlite3'

def get_db_connection():
    # Use a context manager for the connection to ensure it closes
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS card_phone (
                credit_card TEXT NOT NULL,
                phone TEXT NOT NULL,
                PRIMARY KEY (credit_card, phone)
            )
        ''')
        conn.commit()

@app.route('/associate_card', methods=['POST'])
def associate_card():
    # Resource Exhaustion/Input Validation: Ensure request is JSON
    if not request.is_json:
        return jsonify({"error": "Invalid request"}), 400
        
    try:
        data = request.get_json()
    except Exception:
        return jsonify({"error": "Invalid request"}), 400

    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid request"}), 400
    
    credit_card = data.get('credit_card')
    phone = data.get('phone')
    
    # Input Validation: Ensure inputs are strings and not excessively long
    # (Preventing potential DoS via massive strings in the DB)
    if not isinstance(credit_card, str) or not isinstance(phone, str):
        return jsonify({"error": "Invalid request"}), 400
    
    if len(credit_card) > 20 or len(phone) > 20:
        return jsonify({"error": "Invalid request"}), 400
    
    try:
        with get_db_connection() as conn:
            # SQL Injection Prevention: Using parameterized queries
            conn.execute('INSERT OR IGNORE INTO card_phone (credit_card, phone) VALUES (?, ?)', 
                         (credit_card, phone))
            conn.commit()
        return '', 201
    except Exception:
        # Error Handling: Return documented 400 without leaking internal stack traces
        return jsonify({"error": "Invalid request"}), 400

@app.route('/retrieve_cards', methods=['POST'])
def retrieve_cards():
    if not request.is_json:
        return jsonify({"error": "Invalid request"}), 400
        
    try:
        data = request.get_json()
    except Exception:
        return jsonify({"error": "Invalid request"}), 400

    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid request"}), 400
    
    phone_numbers = data.get('phone_numbers')
    
    # Input Validation: Ensure phone_numbers is a list of strings
    if not isinstance(phone_numbers, list):
        return jsonify({"error": "Invalid request"}), 400
    
    # Resource Exhaustion: Limit the number of phone numbers to prevent CPU/DB spikes
    if len(phone_numbers) > 100:
        return jsonify({"error": "Invalid request"}), 400

    for p in phone_numbers:
        if not isinstance(p, str) or len(p) > 20:
            return jsonify({"error": "Invalid request"}), 400
    
    if not phone_numbers:
        return jsonify({"card_numbers": []}), 200

    try:
        with get_db_connection() as conn:
            # SQL Injection Prevention: 
            # 1. The number of placeholders is derived from the length of the list (integer).
            # 2. The values are passed as parameters.
            placeholders = ','.join(['?'] * len(phone_numbers))
            query = f'''
                SELECT credit_card 
                FROM card_phone 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            '''
            params = phone_numbers + [len(phone_numbers)]
            rows = conn.execute(query, params).fetchall()
            
            card_numbers = [row['credit_card'] for row in rows]
            
            if not card_numbers:
                return jsonify({"error": "Not found"}), 404
                
            return jsonify({"card_numbers": card_numbers}), 200
    except Exception:
        # Error Handling: Return documented 400 without leaking internal details
        return jsonify({"error": "Invalid request"}), 400

if __name__ == '__main__':
    init_db()
    # Running on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)