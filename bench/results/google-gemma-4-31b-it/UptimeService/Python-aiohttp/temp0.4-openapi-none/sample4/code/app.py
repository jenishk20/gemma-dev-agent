import os
import sqlite3
import datetime
from aiohttp import web

# Database configuration
DB_PATH = "db.sqlite3"

def init_db():
    """Initialize the SQLite database and create the services table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            serviceId TEXT PRIMARY KEY,
            token TEXT NOT NULL,
            lastNotification TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

async def handle_heartbeat(request):
    """
    POST /heartbeat
    Registers a heartbeat for a specific service.
    """
    try:
        data = await request.json()
    except Exception:
        return web.response_json({"error": "Invalid JSON"}, status=400)

    service_id = data.get('serviceId')
    token = data.get('token')

    if not service_id or not token:
        return web.response_json({"error": "Missing serviceId or token"}, status=400)

    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Upsert: update if exists, otherwise insert
        cursor.execute('''
            INSERT INTO services (serviceId, token, lastNotification) 
            VALUES (?, ?, ?)
            ON CONFLICT(serviceId) DO UPDATE SET 
                token=excluded.token, 
                lastNotification=excluded.lastNotification
        ''', (service_id, token, now))
        conn.commit()
        conn.close()
        return web.Response(status=200)
    except Exception as e:
        print(f"Database error: {e}")
        return web.Response(status=500)

async def handle_services(request):
    """
    POST /services
    Returns a list of services associated with the provided token.
    """
    try:
        data = await request.json()
    except Exception:
        return web.response_json({"error": "Invalid JSON"}, status=400)

    token = data.get('token')
    if not token:
        return web.response_json({"error": "Missing token"}, status=400)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT serviceId, lastNotification FROM services WHERE token = ?', (token,))
        rows = cursor.fetchall()
        conn.close()

        services_list = [
            {"serviceId": row[0], "lastNotification": row[1]} 
            for row in rows
        ]
        return web.json_response(services_list)
    except Exception as e:
        print(f"Database error: {e}")
        return web.Response(status=500)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/heartbeat', handle_heartbeat),
        web.post('/services', handle_services),
    ])
    return app

if __name__ == '__main__':
    init_db()
    app = None # Placeholder for the async init
    # We use a wrapper to run the async init_app
    import asyncio
    
    async def start_server():
        global app
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        print("Server started at http://0.0.0.0:5000")
        await site.start()
        # Keep the loop running
        await asyncio.Event().wait()

    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        pass