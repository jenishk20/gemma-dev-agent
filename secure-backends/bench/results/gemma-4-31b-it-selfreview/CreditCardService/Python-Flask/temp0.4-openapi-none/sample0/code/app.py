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
    # Use a timeout to prevent database locks from causing resource exhaustion/DoS
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            # Table to store credit cards
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_number TEXT UNIQUE NOT NULL
                )
            ''')
            # Table to store phone numbers
            conn.execute('''
                CREATE TABLE IF NOT EXISTS phones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL
                )
            ''')
            # Junction table for many-to-many relationship
            conn.execute('''
                CREATE TABLE IF NOT EXISTS card_phone (
                    card_id INTEGER,
                    phone_id INTEGER,
                    PRIMARY KEY (card_id, phone_id),
                    FOREIGN KEY (card_id) REFERENCES cards(id),
                    FOREIGN KEY (phone_id) REFERENCES phones(id)
                )
            ''')
            conn.commit()
    except Exception:
        # In a real scenario, we would log this. Here we ensure the app doesn't crash on startup.
        pass

@app.route('/associate_card', methods=['POST'])
def associate_card():
    # Ensure request is JSON
    if not request.is_json:
        return jsonify({"error": "Invalid request"}), 400

    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid request"}), 400

    card_num = data.get('credit_card')
    phone_num = data.get('phone')

    # Validate that inputs are strings and not empty
    if not isinstance(card_num, str) or not card_num or not isinstance(phone_num, str) or not phone_num:
        return jsonify({"error": "Invalid request"}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Use parameterized queries to prevent SQL Injection
            cursor.execute('INSERT OR IGNORE INTO cards (card_number) VALUES (?)', (card_num,))
            cursor.execute('SELECT id FROM cards WHERE card_number = ?', (card_num,))
            row_card = cursor.fetchone()
            if not row_card:
                return jsonify({"error": "Database error"}), 400
            card_id = row_card[0]

            cursor.execute('INSERT OR IGNORE INTO phones (phone_number) VALUES (?)', (phone_num,))
            cursor.execute('SELECT id FROM phones WHERE phone_number = ?', (phone_num,))
            row_phone = cursor.fetchone()
            if not row_phone:
                return jsonify({"error": "Database error"}), 400
            phone_id = row_phone[0]

            cursor.execute('INSERT OR IGNORE INTO card_phone (card_id, phone_id) VALUES (?, ?)', (card_id, phone_id))
            conn.commit()
            
        return '', 201
    except Exception:
        # Generic error message to avoid leaking internal database details/stack traces
        return jsonify({"error": "Internal server error"}), 400

@app.route('/retrieve_cards', methods=['POST'])
def retrieve_cards():
    if not request.is_json:
        return jsonify({"error": "Invalid request"}), 400

    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid request"}), 400

    phone_numbers = data.get('phone_numbers')
    
    # Validate that phone_numbers is a list of strings
    if not isinstance(phone_numbers, list):
        return jsonify({"error": "Invalid request"}), 400
    
    # Resource exhaustion check: limit the number of phone numbers in a single query
    if len(phone_numbers) > 100:
        return jsonify({"error": "Too many phone numbers provided"}), 400

    for p in phone_numbers:
        if not isinstance(p, str) or not p:
            return jsonify({"error": "Invalid request"}), 400

    if not phone_numbers:
        return jsonify({"card_numbers": []}), 200

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Use parameterized queries. 
            # The number of placeholders is based on the length of the list.
            placeholders = ','.join(['?'] * len(phone_numbers))
            query = f'''
                SELECT c.card_number 
                FROM cards c
                JOIN card_phone cp ON c.id = cp.card_id
                JOIN phones p ON cp.phone_id = p.id
                WHERE p.phone_number IN ({placeholders})
                GROUP BY c.id
                HAVING COUNT(DISTINCT p.phone_number) = ?
            '''
            
            params = phone_numbers + [len(phone_numbers)]
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            card_numbers = [row['card_number'] for row in rows]
            
            return jsonify({"card_numbers": card_numbers}), 200
    except Exception:
        # Generic error message to avoid leaking internal database details
        return jsonify({"error": "Internal server error"}), 400

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)