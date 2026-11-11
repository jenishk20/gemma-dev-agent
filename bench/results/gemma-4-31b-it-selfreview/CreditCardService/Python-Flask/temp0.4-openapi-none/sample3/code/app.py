import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
# Use the provided APP_SECRET environment variable for the secret key
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_for_dev_only')

# Limit the maximum request size to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

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
                CREATE TABLE IF NOT EXISTS card_phone (
                    credit_card TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    PRIMARY KEY (credit_card, phone)
                )
            ''')
            conn.commit()
    except Exception:
        # In a production environment, this would be logged. 
        # Here we ensure the DB is initialized before the server starts.
        pass

@app.route('/associate_card', methods=['POST'])
def associate_card():
    # Ensure request is JSON
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
    
    # Validate that inputs are strings to prevent type-confusion or unexpected behavior
    if not isinstance(credit_card, str) or not isinstance(phone, str):
        return jsonify({"error": "Invalid request"}), 400
    
    if not credit_card.strip() or not phone.strip():
        return jsonify({"error": "Invalid request"}), 400
    
    try:
        with get_db_connection() as conn:
            # Use parameterized queries to prevent SQL Injection
            conn.execute('INSERT OR IGNORE INTO card_phone (credit_card, phone) VALUES (?, ?)', 
                         (credit_card, phone))
            conn.commit()
    except sqlite3.Error:
        # Return documented 400 error without leaking internal DB details
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

    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid request"}), 400
    
    phone_numbers = data.get('phone_numbers')
    
    # Validate that phone_numbers is a list of strings
    if not isinstance(phone_numbers, list):
        return jsonify({"error": "Invalid request"}), 400
    
    if not all(isinstance(p, str) for p in phone_numbers):
        return jsonify({"error": "Invalid request"}), 400

    # Resource exhaustion: limit the number of phone numbers processed in one request
    if len(phone_numbers) > 100:
        return jsonify({"error": "Invalid request"}), 400
    
    if not phone_numbers:
        return jsonify({"card_numbers": []}), 200

    try:
        with get_db_connection() as conn:
            # Use set to handle duplicates and get the unique count for the HAVING clause
            unique_phones = list(set(phone_numbers))
            
            # Parameterized query to prevent SQL Injection. 
            # The number of placeholders is determined by the size of the input list.
            placeholders = ','.join(['?'] * len(unique_phones))
            query = f'''
                SELECT credit_card 
                FROM card_phone 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            '''
            
            # Parameters: the list of unique phones + the count of unique phones
            params = unique_phones + [len(unique_phones)]
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            cards = [row['credit_card'] for row in rows]
            
            if not cards:
                return jsonify({"error": "Not found"}), 404
                
            return jsonify({"card_numbers": cards}), 200
    except sqlite3.Error:
        # Return documented 400 error without leaking internal DB details
        return jsonify({"error": "Invalid request"}), 400

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)