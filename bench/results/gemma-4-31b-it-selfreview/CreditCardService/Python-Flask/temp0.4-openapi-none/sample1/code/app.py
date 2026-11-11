import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
# Use the provided APP_SECRET env variable for the secret key
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key')

# Limit request body size to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

DB_NAME = 'db.sqlite3'

def get_db_connection():
    # Use a context manager for connections to ensure they are closed
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS card_phone_associations (
                    card_number TEXT,
                    phone_number TEXT,
                    PRIMARY KEY (card_number, phone_number)
                )
            ''')
            conn.commit()
    except Exception:
        # In a real production app, we would log this. 
        # Here we ensure the server doesn't crash during init.
        pass

@app.route('/associate_card', methods=['POST'])
def associate_card():
    # Ensure the request is JSON
    if not request.is_json:
        return jsonify({"error": "Invalid request"}), 400
    
    try:
        data = request.get_json()
    except Exception:
        return jsonify({"error": "Invalid request"}), 400

    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    card = data.get('credit_card')
    phone = data.get('phone')
    
    # Validate that inputs are strings to prevent type-confusion or unexpected behavior
    if not isinstance(card, str) or not isinstance(phone, str):
        return jsonify({"error": "Invalid request"}), 400
    
    if not card.strip() or not phone.strip():
        return jsonify({"error": "Invalid request"}), 400
    
    try:
        with get_db_connection() as conn:
            # Use parameterized queries to prevent SQL Injection
            conn.execute(
                'INSERT OR IGNORE INTO card_phone_associations (card_number, phone_number) VALUES (?, ?)', 
                (card, phone)
            )
            conn.commit()
    except Exception:
        # Return a generic 400 error to avoid leaking internal database details/stack traces
        return jsonify({"error": "Invalid request"}), 400
        
    return '', 201

@app.route('/retrieve_cards', methods=['POST'])
def retrieve_cards():
    if not request.is_json:
        return jsonify({"error": "Invalid request"}), 400
    
    try:
        data = request.get_json()
    except Exception:
        return jsonify({"error": "Invalid request"}), 400

    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    phone_numbers = data.get('phone_numbers')
    
    # Strict validation of the input array
    if phone_numbers is None or not isinstance(phone_numbers, list):
        return jsonify({"error": "Invalid request"}), 400
    
    # Resource exhaustion check: limit the number of phone numbers processed in one request
    if len(phone_numbers) > 100:
        return jsonify({"error": "Too many phone numbers"}), 400

    # Validate that every element in the list is a string
    if not all(isinstance(p, str) for p in phone_numbers):
        return jsonify({"error": "Invalid request"}), 400

    if not phone_numbers:
        return jsonify({"card_numbers": []}), 200

    try:
        with get_db_connection() as conn:
            # To find cards associated with ALL given phone numbers:
            # We use a parameterized query. 
            # The number of placeholders is determined by the input list length.
            # We use a set to handle duplicate phone numbers in the input list.
            unique_phones = list(set(phone_numbers))
            placeholders = ','.join(['?'] * len(unique_phones))
            
            query = f'''
                SELECT card_number 
                FROM card_phone_associations 
                WHERE phone_number IN ({placeholders}) 
                GROUP BY card_number 
                HAVING COUNT(DISTINCT phone_number) = ?
            '''
            
            # Parameters are passed separately to the execute method to prevent SQLi
            params = unique_phones + [len(unique_phones)]
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            cards = [row['card_number'] for row in rows]
            
            return jsonify({"card_numbers": cards}), 200
    except Exception:
        # Return a generic 400 error to avoid leaking internal database details/stack traces
        return jsonify({"error": "Invalid request"}), 400

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)