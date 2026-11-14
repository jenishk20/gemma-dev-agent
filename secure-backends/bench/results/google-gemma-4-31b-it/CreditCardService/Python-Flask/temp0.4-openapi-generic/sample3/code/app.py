import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_NAME = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Create table for associations
        # Using a composite primary key to prevent duplicate card-phone pairs
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
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    credit_card = data.get('credit_card')
    phone = data.get('phone')

    if not credit_card or not phone:
        return jsonify({"error": "Missing credit_card or phone"}), 400

    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO card_phone_associations (credit_card, phone) VALUES (?, ?)",
                (credit_card, phone)
            )
            conn.commit()
    except sqlite3.Error as e:
        return jsonify({"error": "Database error"}), 500

    return '', 201

@app.route('/retrieve_cards', methods=['POST'])
def retrieve_cards():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    phone_numbers = data.get('phone_numbers')
    if not isinstance(phone_numbers, list):
        return jsonify({"error": "phone_numbers must be an array"}), 400

    if not phone_numbers:
        return jsonify({"card_numbers": []}), 200

    try:
        with get_db_connection() as conn:
            # To find cards associated with ALL provided phone numbers:
            # 1. Filter for cards associated with any of the phones.
            # 2. Group by card.
            # 3. Filter groups where the count of distinct phones equals the count of requested phones.
            
            # We use a parameterized query to prevent SQL injection
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
            results = [row['credit_card'] for row in cursor.fetchall()]
            
            if not results:
                return jsonify({"card_numbers": []}), 200
                
            return jsonify({"card_numbers": results}), 200

    except sqlite3.Error as e:
        return jsonify({"error": "Database error"}), 500

if __name__ == '__main__':
    init_db()
    # Running on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)