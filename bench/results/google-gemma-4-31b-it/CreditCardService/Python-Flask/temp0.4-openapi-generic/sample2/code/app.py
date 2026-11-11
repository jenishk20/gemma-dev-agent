import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_for_dev')

DB_FILE = 'db.sqlite3'

def get_db_connection():
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema."""
    with get_db_connection() as conn:
        # We use a junction table to associate cards with phones.
        # Unique constraint ensures no duplicate associations.
        conn.execute('''
            CREATE TABLE IF NOT EXISTS card_phone_associations (
                credit_card TEXT NOT NULL,
                phone TEXT NOT NULL,
                PRIMARY KEY (credit_card, phone)
            )
        ''')
        conn.commit()

@app.route('/associate_card', methods=['POST'])
def associate_card():
    """
    Create a new association of a credit card number with a phone number.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request, JSON body required"}), 400

    credit_card = data.get('credit_card')
    phone = data.get('phone')

    if not credit_card or not phone:
        return jsonify({"error": "Missing credit_card or phone"}), 400

    try:
        with get_db_connection() as conn:
            conn.execute(
                'INSERT OR IGNORE INTO card_phone_associations (credit_card, phone) VALUES (?, ?)',
                (credit_card, phone)
            )
            conn.commit()
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

    return '', 201

@app.route('/retrieve_cards', methods=['POST'])
def retrieve_cards():
    """
    Retrieve cards associated with a set of phone numbers. 
    A card must be associated with ALL given phone numbers to be returned.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request, JSON body required"}), 400

    phone_numbers = data.get('phone_numbers')
    if not isinstance(phone_numbers, list):
        return jsonify({"error": "phone_numbers must be an array"}), 400

    if not phone_numbers:
        return jsonify({"card_numbers": []}), 200

    try:
        with get_db_connection() as conn:
            # To find cards associated with ALL phones in the list:
            # We group by credit_card and filter for those where the count of 
            # distinct phones associated with that card matches the size of the input list.
            # We use a parameterized query to prevent SQL injection.
            
            placeholders = ','.join(['?'] * len(phone_numbers))
            query = f'''
                SELECT credit_card 
                FROM card_phone_associations 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            '''
            
            params = phone_numbers + [len(phone_numbers)]
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            card_numbers = [row['credit_card'] for row in rows]
            
            if not card_numbers:
                return jsonify({"error": "Not found"}), 404
                
            return jsonify({"card_numbers": card_numbers}), 200

    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)