import os
import sqlite3
import datetime
from aiohttp import web

# Database configuration
DB_NAME = "db.sqlite3"

def init_db():
    """Initialize the SQLite database and create the services table."""
    conn = sqlite3.connect(DB_NAME)
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
        return web.json_response({"error": "Invalid JSON"}, status=400)

    service_id = data.get('serviceId')
    token = data.get('token')

    if not service_id or not token:
        return web.json_response({"error": "Missing serviceId or token"}, status=400)

    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Upsert: Insert new service or update existing one
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
        return web.json_response({"error": "Internal server error"}, status=500)

async def handle_services(request):
    """
    POST /services
    Returns an overview of services registered with the provided token.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    token = data.get('token')
    if not token:
        return web.json_response({"error": "Missing token"}, status=400)

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT serviceId, lastNotification FROM services WHERE token = ?', (token,))
        rows = cursor.fetchall()
        conn.close()

        results = [{"serviceId": row[0], "lastNotification": row[1]} for row in rows]
        return web.json_response(results, status=200)
    except Exception as e:
        print(f"Database error: {e}")
        return web.json_response({"error": "Internal server error"}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/heartbeat', handle_heartbeat),
        web.post('/services', handle_services),
    ])
    return app

if __name__ == '__main__':
    # Ensure database is initialized before starting the server
    init_db()
    
    # Start the aiohttp server
    app = None # Placeholder for async init if needed, but we can just run it
    web.run_app(
        web.Application().add_routes([
            web.post('/heartbeat', handle_heartbeat),
            web.post('/services', handle_services),
        ]), 
        port=5000, 
        address='0.0.0.0'
    )