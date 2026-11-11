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
        # We use a table to store the association between cards and phones
        # A card can be associated with multiple phones
        conn.execute('''
            CREATE TABLE IF NOT EXISTS card_phone_associations (
                card_number TEXT,
                phone_number TEXT,
                PRIMARY KEY (card_number, phone_number)
            )
        ''')
        conn.commit()

@app.route('/associate_card', methods=['POST'])
def associate_card():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    card = data.get('credit_card')
    phone = data.get('phone')
    
    if not card or not phone:
        return jsonify({"error": "Missing credit_card or phone"}), 400
    
    try:
        with get_db_connection() as conn:
            conn.execute(
                'INSERT OR IGNORE INTO card_phone_associations (card_number, phone_number) VALUES (?, ?)', 
                (card, phone)
            )
            conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 400
        
    return '', 201

@app.route('/retrieve_cards', methods=['POST'])
def retrieve_cards():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    phone_numbers = data.get('phone_numbers')
    if phone_numbers is None or not isinstance(phone_numbers, list):
        return jsonify({"error": "phone_numbers must be a list"}), 400
    
    if not phone_numbers:
        return jsonify({"card_numbers": []}), 200

    try:
        with get_db_connection() as conn:
            # To find cards associated with ALL given phone numbers:
            # We group by card_number and filter for those where the count of 
            # distinct phone numbers matching the input list equals the size of the input list.
            placeholders = ','.join(['?'] * len(phone_numbers))
            query = f'''
                SELECT card_number 
                FROM card_phone_associations 
                WHERE phone_number IN ({placeholders}) 
                GROUP BY card_number 
                HAVING COUNT(DISTINCT phone_number) = ?
            '''
            params = phone_numbers + [len(set(phone_numbers))]
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            cards = [row['card_number'] for row in rows]
            
            if not cards:
                return jsonify({"card_numbers": []}), 200 # Returning empty list as per standard API behavior for "not found" in lists
            
            return jsonify({"card_numbers": cards}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)