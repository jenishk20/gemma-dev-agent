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
        return web.json_response({"error": "Invalid JSON payload"}, status=400)

    service_id = data.get('serviceId')
    token = data.get('token')

    if not service_id or not token:
        return web.json_response({"error": "Missing serviceId or token"}, status=400)

    try:
        now = datetime.datetime.utcnow().isoformat()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Use UPSERT logic (INSERT OR REPLACE) to update the heartbeat
        cursor.execute(
            "INSERT OR REPLACE INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)",
            (service_id, token, now)
        )
        conn.commit()
        conn.close()
        return web.json_response({"status": "Heartbeat registered successfully"}, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_get_services(request):
    """
    POST /services
    Returns an overview of services registered with the provided token.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON payload"}, status=400)

    token = data.get('token')
    if not token:
        return web.json_response({"error": "Missing token"}, status=400)

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT serviceId, lastNotification FROM services WHERE token = ?", (token,))
        rows = cursor.fetchall()
        conn.close()

        services_list = [
            {"serviceId": row[0], "lastNotification": row[1]} 
            for row in rows
        ]
        return web.json_response(services_list, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

def main():
    # Initialize DB
    init_db()

    app = web.Application()
    
    # Routes
    app.add_routes([
        web.post('/heartbeat', handle_heartbeat),
        web.post('/services', handle_get_services),
    ])

    # Start the server on 0.0.0.0:5000
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()