import os
import sqlite3
import asyncio
from aiohttp import web

# Database configuration
DB_NAME = "db.sqlite3"

def init_db():
    """Initialize the SQLite database and create the necessary table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Table to store the association between cards and phones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_phone (
            card_number TEXT,
            phone_number TEXT,
            PRIMARY KEY (card_number, phone_number)
        )
    ''')
    conn.commit()
    conn.close()

async def associate_card(request):
    """
    POST /associate_card
    Creates a new association of a credit card number with a phone number.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    card = data.get('credit_card')
    phone = data.get('phone')

    if not card or not phone:
        return web.json_response({"error": "Missing credit_card or phone"}, status=400)

    try:
        # Use a synchronous connection in a thread pool via run_in_executor if it were high load,
        # but for this implementation, we use standard sqlite3.
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO card_phone (card_number, phone_number) VALUES (?, ?)', (card, phone))
        conn.commit()
        conn.close()
        return web.Response(status=201)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def retrieve_cards(request):
    """
    POST /retrieve_cards
    Retrieve cards associated with ALL given phone numbers.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    phone_numbers = data.get('phone_numbers')

    if not isinstance(phone_numbers, list):
        return web.json_response({"error": "phone_numbers must be an array"}, status=400)

    if not phone_numbers:
        return web.json_response({"card_numbers": []}, status=200)

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # To find cards associated with ALL given phones:
        # Select card_numbers where the count of distinct phone numbers associated with that card
        # matches the number of phones requested, and the phones are within the requested set.
        placeholders = ','.join(['?'] * len(phone_numbers))
        query = f'''
            SELECT card_number 
            FROM card_phone 
            WHERE phone_number IN ({placeholders}) 
            GROUP BY card_number 
            HAVING COUNT(DISTINCT phone_number) = ?
        '''
        params = phone_numbers + [len(phone_numbers)]
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        conn.close()
        
        card_list = [row[0] for row in rows]
        
        if not card_list:
            return web.json_response({"error": "Not found"}, status=404)
            
        return web.json_response({"card_numbers": card_list}, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/associate_card', associate_card),
        web.post('/retrieve_cards', retrieve_cards),
    ])
    return app

if __name__ == '__main__':
    init_db()
    app = asyncio.run(init_app()) # This is a helper, but we need to run the loop
    # Correct way to run aiohttp app in a script:
    web.run_app(asyncio.run(init_app()), port=5000, address='0.0.0.0')

# Re-adjusting the main block to avoid asyncio.run conflict with run_app
def main():
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/associate_card', associate_card),
        web.post('/retrieve_cards', retrieve_cards),
    ])
    web.run_app(app, port=5000, address='0.0.0.0')

if __name__ == '__main__':
    main()