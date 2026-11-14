import os
import sqlite3
import asyncio
from aiohttp import web

# Database initialization
DB_NAME = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Create table for associations
        # We use a unique constraint to prevent duplicate associations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS associations (
                credit_card TEXT,
                phone TEXT,
                PRIMARY KEY (credit_card, phone)
            )
        ''')
        conn.commit()

async def associate_card(request):
    try:
        data = await request.json()
    except Exception:
        return web.response.json({"error": "Invalid JSON"}, status=400)

    credit_card = data.get('credit_card')
    phone = data.get('phone')

    if not credit_card or not phone:
        return web.response.json({"error": "Missing credit_card or phone"}, status=400)

    try:
        # Using run_in_executor to avoid blocking the event loop with sqlite3
        def db_op():
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO associations (credit_card, phone) VALUES (?, ?)", 
                    (credit_card, phone)
                )
                conn.commit()
        
        await asyncio.get_event_loop().run_in_executor(None, db_op)
        return web.Response(status=201)
    except Exception as e:
        return web.response.json({"error": str(e)}, status=500)

async def retrieve_cards(request):
    try:
        data = await request.json()
    except Exception:
        return web.response.json({"error": "Invalid JSON"}, status=400)

    phone_numbers = data.get('phone_numbers')

    if not isinstance(phone_numbers, list):
        return web.response.json({"error": "phone_numbers must be an array"}, status=400)

    if not phone_numbers:
        return web.response.json({"card_numbers": []}, status=200)

    try:
        def db_op():
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                # To find cards associated with ALL given phone numbers:
                # We filter for the phones, group by card, and ensure the count of distinct phones matches the input list length
                placeholders = ','.join(['?'] * len(phone_numbers))
                query = f'''
                    SELECT credit_card 
                    FROM associations 
                    WHERE phone IN ({placeholders}) 
                    GROUP BY credit_card 
                    HAVING COUNT(DISTINCT phone) = ?
                '''
                params = phone_numbers + [len(phone_numbers)]
                cursor.execute(query, params)
                return [row[0] for row in cursor.fetchall()]

        cards = await asyncio.get_event_loop().run_in_executor(None, db_op)
        
        if not cards:
            # The schema mentions 404 for Not Found, though 200 with empty list is more common for search
            # We follow the schema's 404 possibility if no cards are found
            return web.response.json({"card_numbers": []}, status=404)
            
        return web.response.json({"card_numbers": cards}, status=200)
    except Exception as e:
        return web.response.json({"error": str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/associate_card', associate_card),
        web.post('/retrieve_cards', retrieve_cards),
    ])
    return app

if __name__ == '__main__':
    init_db()
    app = asyncio.run(init_app()) # This is slightly wrong for aiohttp, let's use standard run_app
    
def start_server():
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/associate_card', associate_card),
        web.post('/retrieve_cards', retrieve_cards),
    ])
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    start_server()