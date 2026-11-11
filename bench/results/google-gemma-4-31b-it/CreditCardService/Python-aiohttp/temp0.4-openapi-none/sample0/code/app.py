import os
import sqlite3
import asyncio
from aiohttp import web

# Database configuration
DB_PATH = "db.sqlite3"

async def init_db():
    """Initialize the SQLite database and create the necessary table."""
    # Using a synchronous connection for initialization
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Table to store associations between cards and phones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_phone (
            card_number TEXT,
            phone_number TEXT,
            PRIMARY KEY (card_number, phone_number)
        )
    ''')
    conn.commit()
    conn.close()

async def run_query(query, params=()):
    """Helper to run sqlite queries in a thread pool to avoid blocking the event loop."""
    def _execute():
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _execute)

async def associate_card(request):
    """
    POST /associate_card
    Associates a credit card number with a phone number.
    """
    try:
        data = await request.json()
    except Exception:
        return web.response_json({'error': 'Invalid JSON'}, status=400)

    card = data.get('credit_card')
    phone = data.get('phone')

    if not card or not phone:
        return web.response_json({'error': 'Missing credit_card or phone'}, status=400)

    # Insert or ignore if the association already exists
    await run_query(
        "INSERT OR IGNORE INTO card_phone (card_number, phone_number) VALUES (?, ?)", 
        (card, phone)
    )
    
    return web.Response(status=201)

async def retrieve_cards(request):
    """
    POST /retrieve_cards
    Retrieves cards associated with ALL provided phone numbers.
    """
    try:
        data = await request.json()
    except Exception:
        return web.response_json({'error': 'Invalid JSON'}, status=400)

    phone_numbers = data.get('phone_numbers')

    if not isinstance(phone_numbers, list):
        return web.response_json({'error': 'phone_numbers must be a list'}, status=400)

    if not phone_numbers:
        return web.response_json({'card_numbers': []}, status=200)

    # To find cards associated with ALL given phone numbers, we can use:
    # SELECT card_number FROM card_phone WHERE phone_number IN (...) 
    # GROUP BY card_number HAVING COUNT(DISTINCT phone_number) = len(phone_numbers)
    
    placeholders = ', '.join(['?'] * len(phone_numbers))
    query = f"""
        SELECT card_number 
        FROM card_phone 
        WHERE phone_number IN ({placeholders}) 
        GROUP BY card_number 
        HAVING COUNT(DISTINCT phone_number) = ?
    """
    
    params = tuple(phone_numbers) + (len(phone_numbers),)
    results = await run_query(query, params)
    
    card_list = [row[0] for row in results]
    
    if not card_list:
        # The schema allows 404 for Not Found, but usually 200 with empty list is preferred.
        # However, following the schema's 404 option:
        return web.response_json({'error': 'No cards found'}, status=404)

    return web.response_json({'card_numbers': card_list}, status=200)

async def init_app():
    """Initialize the aiohttp application."""
    await init_db()
    app = web.Application()
    app.add_routes([
        web.post('/associate_card', associate_card),
        web.post('/retrieve_cards', retrieve_cards),
    ])
    return app

if __name__ == '__main__':
    app = asyncio.run(init_app()) # This is a bit wrong for aiohttp, usually we use web.run_app
    # Correct way to start aiohttp server:
    async def start_server():
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(app, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        while True:
            await asyncio.sleep(3600)

    # Since we need a runnable script:
    try:
        # Use the standard web.run_app for simplicity, but we need to init_db first
        async def main():
            await init_db()
            app = web.Application()
            app.add_routes([
                web.post('/associate_card', associate_card),
                web.post('/retrieve_cards', retrieve_cards),
            ])
            web.run_app(app, host='0.0.0.0', port=5000)
        
        # To handle the async init_db before run_app (which is blocking)
        # we can just run init_db in a separate loop or use a startup signal.
        
        # Revised approach for aiohttp:
        app = web.Application()
        app.add_routes([
            web.post('/associate_card', associate_card),
            web.post('/retrieve_cards', retrieve_cards),
        ])
        
        async def on_startup(app):
            await init_db()
            
        app.on_startup.append(on_startup)
        web.run_app(app, host='0.0.0.0', port=5000)
    except Exception as e:
        pass