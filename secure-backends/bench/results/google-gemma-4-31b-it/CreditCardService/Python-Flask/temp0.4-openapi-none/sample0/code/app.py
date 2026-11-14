import os
import sqlite3
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

@app.route('/associate_card', methods=['POST'])
def associate_card():
    data = request.get_json()
    if not data or 'credit_card' not in data or 'phone' not in data:
        return jsonify({"error": "Invalid request"}), 400

    card_num = data['credit_card']
    phone_num = data['phone']

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Ensure card exists
            cursor.execute('INSERT OR IGNORE INTO cards (card_number) VALUES (?)', (card_num,))
            cursor.execute('SELECT id FROM cards WHERE card_number = ?', (card_num,))
            card_id = cursor.fetchone()[0]

            # Ensure phone exists
            cursor.execute('INSERT OR IGNORE INTO phones (phone_number) VALUES (?)', (phone_num,))
            cursor.execute('SELECT id FROM phones WHERE phone_number = ?', (phone_num,))
            phone_id = cursor.fetchone()[0]

            # Create association
            cursor.execute('INSERT OR IGNORE INTO card_phone (card_id, phone_id) VALUES (?, ?)', (card_id, phone_id))
            conn.commit()
            
        return '', 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/retrieve_cards', methods=['POST'])
def retrieve_cards():
    data = request.get_json()
    if not data or 'phone_numbers' not in data or not isinstance(data['phone_numbers'], list):
        return jsonify({"error": "Invalid request"}), 400

    phone_numbers = data['phone_numbers']
    if not phone_numbers:
        return jsonify({"card_numbers": []}), 200

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Query to find cards associated with ALL provided phone numbers
            # We group by card_id and count how many of the target phones are associated with it.
            # If the count equals the number of target phones, it's a match.
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
            
            if not card_numbers:
                return jsonify({"card_numbers": []}), 200 # Or 404 based on schema, but 200 with empty list is standard for search
            
            return jsonify({"card_numbers": card_numbers}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)