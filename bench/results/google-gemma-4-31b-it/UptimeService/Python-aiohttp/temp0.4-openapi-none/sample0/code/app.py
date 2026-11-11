import os
import sqlite3
import asyncio
from datetime import datetime
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

async def heartbeat_handler(request):
    """
    POST /heartbeat
    Registers a heartbeat for a specific service.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON payload"}, status=400)

    service_id = data.get("serviceId")
    token = data.get("token")

    if not service_id or not token:
        return web.json_response({"error": "Missing serviceId or token"}, status=400)

    try:
        # Use a synchronous connection in a thread to avoid blocking the event loop
        def update_heartbeat():
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute(
                "INSERT OR REPLACE INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)",
                (service_id, token, now)
            )
            conn.commit()
            conn.close()

        await asyncio.to_thread(update_heartbeat)
        return web.Response(status=200)
    except Exception as e:
        print(f"Error updating heartbeat: {e}")
        return web.json_response({"error": "Internal server error"}, status=500)

async def services_handler(request):
    """
    POST /services
    Returns an overview of services associated with the provided token.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON payload"}, status=400)

    token = data.get("token")
    if not token:
        return web.json_response({"error": "Missing token"}, status=400)

    try:
        def get_services():
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT serviceId, lastNotification FROM services WHERE token = ?", (token,))
            rows = cursor.fetchall()
            conn.close()
            return rows

        results = await asyncio.to_thread(get_services)
        
        # Map rows to the expected JSON format
        services_list = [
            {"serviceId": row[0], "lastNotification": row[1]} 
            for row in results
        ]
        
        return web.json_response(services_list, status=200)
    except Exception as e:
        print(f"Error fetching services: {e}")
        return web.json_response({"error": "Internal server error"}, status=500)

async def init_app():
    """Initialize the aiohttp application."""
    app = web.Application()
    app.add_routes([
        web.post('/heartbeat', heartbeat_handler),
        web.post('/services', services_handler),
    ])
    return app

if __name__ == "__main__":
    # Ensure DB is initialized before starting the server
    init_db()
    
    # Create the app and run the server
    app = asyncio.run(init_app())
    web.run_app(app, host='0.0.0.0', port=5000)