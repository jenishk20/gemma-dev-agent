import os
import sqlite3
import uuid
from datetime import datetime
from aiohttp import web

# Database configuration
DB_PATH = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS clicks (id TEXT PRIMARY KEY, timestamp TEXT)"
        )
        conn.commit()

async def handle_post_click(request):
    """
    Register a click. 
    The schema doesn't specify a request body, so we generate a unique ID and timestamp.
    """
    try:
        click_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO clicks (id, timestamp) VALUES (?, ?)", 
                (click_id, timestamp)
            )
            conn.commit()
            
        return web.Response(status=201)
    except Exception:
        return web.Response(status=400, text="Invalid request")

async def handle_get_clicks(request):
    """
    Retrieve clicks based on date and direction.
    """
    date_str = request.query.get('date')
    direction = request.query.get('direction')

    if not date_str or not direction:
        return web.Response(status=400, text="Missing required query parameters: date and direction")

    if direction not in ["<", ">", "<=", ">="]:
        return web.Response(status=400, text="Invalid direction. Must be one of <, >, <=, >=")

    try:
        # Validate date format (YYYY-MM-DD)
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return web.Response(status=400, text="Invalid date format. Use YYYY-MM-DD")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Use a parameterized query for the date, but the operator must be handled carefully.
            # Since the operator is validated against a strict enum, it is safe to interpolate.
            query = f"SELECT id, timestamp FROM clicks WHERE date(timestamp) {direction} ?"
            cursor = conn.execute(query, (date_str,))
            rows = cursor.fetchall()

        if not rows:
            return web.Response(status=404, text="No clicks found")

        clicks = [{"id": row[0], "timestamp": row[1]} for row in rows]
        return web.json_response(clicks)
    except Exception as e:
        return web.Response(status=400, text=str(e))

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/click', handle_post_click),
        web.get('/clicks', handle_get_clicks),
    ])
    return app

if __name__ == "__main__":
    init_db()
    web.run_app(init_app(), port=5000, address='0.0.0.0')