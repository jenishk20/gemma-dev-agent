import asyncio
import sqlite3
import uuid
from datetime import datetime
from aiohttp import web

# Database configuration
DB_NAME = "db.sqlite3"

def init_db():
    """Initialize the SQLite database and create the clicks table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clicks (
            id TEXT PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

async def register_click(request):
    """
    POST /click
    Registers a user's click in the database.
    """
    try:
        # Generate a unique ID and current timestamp
        click_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        # Use a thread pool for blocking sqlite3 calls
        def save_click():
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", (click_id, timestamp))
            conn.commit()
            conn.close()

        await asyncio.to_thread(save_click)
        return web.Response(status=201)
    except Exception:
        return web.Response(status=400, text="Invalid request")

async def retrieve_clicks(request):
    """
    GET /clicks
    Retrieves clicks based on date and direction.
    """
    date_str = request.query.get('date')
    direction = request.query.get('direction')

    if not date_str or not direction:
        return web.Response(status=400, text="Missing required query parameters: date and direction")

    if direction not in ["<", ">", "<=", ">="]:
        return web.Response(status=400, text="Invalid direction parameter")

    try:
        # Validate date format (YYYY-MM-DD)
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return web.Response(status=400, text="Invalid date format. Expected YYYY-MM-DD")

    def fetch_clicks():
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # We use a parameterized query for the date, but the operator (direction) 
        # must be handled carefully. Since we validated direction against a strict 
        # whitelist, it is safe to interpolate.
        query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
        cursor.execute(query, (date_str,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    rows = await asyncio.to_thread(fetch_clicks)
    
    if not rows:
        return web.Response(status=404, text="No clicks found")

    # Convert rows to list of dicts
    results = [{"id": row["id"], "timestamp": row["timestamp"]} for row in rows]
    return web.json_response(results, status=200)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/click', register_click),
        web.get('/clicks', retrieve_clicks),
    ])
    return app

if __name__ == "__main__":
    init_db()
    app = asyncio.run(init_app()) # This is a helper, but we need to run it via web.run_app
    # Re-initializing properly for the runner
    async def start():
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        await asyncio.Event().wait()

    # Standard aiohttp entry point
    app_instance = asyncio.run(init_app())
    web.run_app(app_instance, port=5000, address='0.0.0.0')