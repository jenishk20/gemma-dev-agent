import os
import sqlite3
import asyncio
from aiohttp import web

# Database helper to handle synchronous sqlite3 calls in a thread pool
async def run_query(query, params=(), fetch=False):
    def _execute():
        with sqlite3.connect('db.sqlite3') as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()
            return None
    return await asyncio.to_thread(_execute)

async def init_db():
    query = """
    CREATE TABLE IF NOT EXISTS card_phone (
        card_number TEXT,
        phone_number TEXT,
        PRIMARY KEY (card_number, phone_number)
    );
    """
    await run_query(query)

async def handle_associate_card(request):
    try:
        data = await request.json()
        card = data.get('credit_card')
        phone = data.get('phone')

        if not card or not phone:
            return web.json_response({"error": "Missing credit_card or phone"}, status=400)

        query = "INSERT OR IGNORE INTO card_phone (card_number, phone_number) VALUES (?, ?)"
        await run_query(query, (card, phone))
        
        return web.Response(status=201)
    except Exception:
        return web.json_response({"error": "Invalid request"}, status=400)

async def handle_retrieve_cards(request):
    try:
        data = await request.json()
        phones = data.get('phone_numbers')

        if not isinstance(phones, list):
            return web.json_response({"error": "phone_numbers must be a list"}, status=400)

        if not phones:
            return web.json_response({"card_numbers": []}, status=200)

        # To find cards associated with ALL provided phone numbers:
        # We group by card_number and filter for those where the count of distinct 
        # phone numbers matches the length of the input list.
        placeholders = ', '.join(['?'] * len(phones))
        query = f"""
        SELECT card_number 
        FROM card_phone 
        WHERE phone_number IN ({placeholders}) 
        GROUP BY card_number 
        HAVING COUNT(DISTINCT phone_number) = ?
        """
        
        params = tuple(phones) + (len(phones),)
        results = await run_query(query, params, fetch=True)
        
        card_numbers = [row[0] for row in results]
        
        if not card_numbers:
            # The schema mentions 404 for not found, though 200 with empty list is common.
            # Following the schema's explicit 404 option.
            return web.json_response({"error": "Not found"}, status=404)

        return web.json_response({"card_numbers": card_numbers}, status=200)
    except Exception:
        return web.json_response({"error": "Invalid request"}, status=400)

async def app_factory():
    await init_db()
    app = web.Application()
    app.add_routes([
        web.post('/associate_card', handle_associate_card),
        web.post('/retrieve_cards', handle_retrieve_cards),
    ])
    return app

if __name__ == '__main__':
    app = asyncio.run(app_factory()) # This is a simplified way to get the app
    # However, aiohttp.web.run_app handles the loop. 
    # Since init_db is async, we use a custom startup.
    
    # Correct way to handle async startup with run_app:
    async def start_server():
        await init_db()
        app = web.Application()
        app.add_routes([
            web.post('/associate_card', handle_associate_card),
            web.post('/retrieve_cards', handle_retrieve_cards),
        ])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        await asyncio.Event().wait()

    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        pass