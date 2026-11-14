import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
# Use the provided APP_SECRET environment variable for the secret key
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_for_dev_only')

DB_NAME = 'db.sqlite3'
# Limit request body size to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS card_phone (
                    credit_card TEXT,
                    phone TEXT,
                    PRIMARY KEY (credit_card, phone)
                )
            ''')
            conn.commit()
    except Exception:
        # In a production environment, we would log this, but for this task 
        # we ensure the DB is initialized.
        pass

@app.route('/associate_card', methods=['POST'])
def associate_card():
    try:
        # Use silent=True to avoid crashing on malformed JSON
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid request"}), 400
        
        credit_card = data.get('credit_card')
        phone = data.get('phone')
        
        # Validate that inputs are strings to prevent type-confusion attacks
        if not isinstance(credit_card, str) or not isinstance(phone, str):
            return jsonify({"error": "Invalid request"}), 400
        
        if not credit_card or not phone:
            return jsonify({"error": "Invalid request"}), 400
        
        with get_db_connection() as conn:
            # Parameterized query prevents SQL Injection
            conn.execute('INSERT OR IGNORE INTO card_phone (credit_card, phone) VALUES (?, ?)', 
                         (credit_card, phone))
            conn.commit()
            
        return '', 201
    except Exception:
        # Generic error handling to prevent leaking internal stack traces
        return jsonify({"error": "Invalid request"}), 400

@app.route('/retrieve_cards', methods=['POST'])
def retrieve_cards():
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid request"}), 400
        
        phone_numbers = data.get('phone_numbers')
        
        # Validate that phone_numbers is a list of strings
        if not isinstance(phone_numbers, list):
            return jsonify({"error": "Invalid request"}), 400
        
        if not all(isinstance(p, str) for p in phone_numbers):
            return jsonify({"error": "Invalid request"}), 400
        
        # Resource exhaustion check: limit the number of phone numbers processed
        if len(phone_numbers) > 100:
            return jsonify({"error": "Invalid request"}), 400

        if not phone_numbers:
            return jsonify({"card_numbers": []}), 200

        with get_db_connection() as conn:
            # Use parameterized queries for the IN clause. 
            # We generate the correct number of '?' placeholders based on input length.
            placeholders = ','.join(['?'] * len(phone_numbers))
            query = f'''
                SELECT credit_card 
                FROM card_phone 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            '''
            params = phone_numbers + [len(phone_numbers)]
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            cards = [row['credit_card'] for row in rows]
            
            return jsonify({"card_numbers": cards}), 200
    except Exception:
        # Generic error handling to prevent leaking internal stack traces
        return jsonify({"error": "Invalid request"}), 400

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)