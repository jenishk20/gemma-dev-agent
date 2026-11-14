import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret')

DB_NAME = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Create table to store the association between cards and phones
        # We use a composite primary key to prevent duplicate associations
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
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    credit_card = data.get('credit_card')
    phone = data.get('phone')
    
    if not credit_card or not phone:
        return jsonify({"error": "Missing credit_card or phone"}), 400
    
    try:
        with get_db_connection() as conn:
            conn.execute('INSERT OR IGNORE INTO card_phone (credit_card, phone) VALUES (?, ?)', 
                         (credit_card, phone))
            conn.commit()
        return '', 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/retrieve_cards', methods=['POST'])
def retrieve_cards():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    phone_numbers = data.get('phone_numbers')
    if not isinstance(phone_numbers, list):
        return jsonify({"error": "phone_numbers must be an array"}), 400
    
    if not phone_numbers:
        return jsonify({"card_numbers": []}), 200

    try:
        with get_db_connection() as conn:
            # To find cards associated with ALL given phone numbers:
            # We filter for the phone numbers, group by card, and ensure the count matches the input list length.
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
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)