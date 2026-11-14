import os
import asyncio
import sqlite3
from aiohttp import web

# Database configuration
DB_NAME = "db.sqlite3"

def init_db():
    """Initialize the SQLite database schema."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Table to store the association between cards and phones
        # We use a composite primary key to prevent duplicate associations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS associations (
                card_number TEXT,
                phone_number TEXT,
                PRIMARY KEY (card_number, phone_number)
            )
        ''')
        conn.commit()

async def associate_card(request):
    """
    POST /associate_card
    Creates a new association of a credit card number with a phone number.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    card = data.get("credit_card")
    phone = data.get("phone")

    if not card or not phone:
        return web.json_response({"error": "Missing credit_card or phone"}, status=400)

    try:
        # Use a thread pool for synchronous sqlite3 calls to avoid blocking the event loop
        def db_insert():
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO associations (card_number, phone_number) VALUES (?, ?)",
                    (card, phone)
                )
                conn.commit()

        await asyncio.to_thread(db_insert)
        return web.Response(status=201)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def retrieve_cards(request):
    """
    POST /retrieve_cards
    Retrieve cards associated with ALL given phone numbers.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    phones = data.get("phone_numbers")

    if not isinstance(phones, list):
        return web.json_response({"error": "phone_numbers must be an array"}, status=400)

    if not phones:
        return web.json_response({"card_numbers": []}, status=200)

    try:
        def db_query():
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                # To find cards associated with ALL provided phones:
                # Filter by the list of phones, group by card, and ensure the count matches the input list size.
                placeholders = ','.join(['?'] * len(phones))
                query = f'''
                    SELECT card_number 
                    FROM associations 
                    WHERE phone_number IN ({placeholders}) 
                    GROUP BY card_number 
                    HAVING COUNT(DISTINCT phone_number) = ?
                '''
                # Parameters: the list of phones + the count of unique phones requested
                params = phones + [len(set(phones))]
                cursor.execute(query, params)
                return [row[0] for row in cursor.fetchall()]

        results = await asyncio.to_thread(db_query)
        
        if not results:
            # The schema specifies 404 for Not Found, though 200 with empty list is also common.
            # Following the schema's 404 response option.
            return web.json_response({"error": "No cards found"}, status=404)
            
        return web.json_response({"card_numbers": results}, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/associate_card', associate_card),
        web.post('/retrieve_cards', retrieve_cards),
    ])
    return app

if __name__ == "__main__":
    init_db()
    app = asyncio.run(init_app()) # This is a helper, but we need to run the runner
    # Correct way to run aiohttp app:
    web.run_app(asyncio.run(init_app()), port=5000)

# Re-writing the main block to be cleaner for the runner
def run():
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/associate_card', associate_card),
        web.post('/retrieve_cards', retrieve_cards),
    ])
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    run()