import os
import sqlite3
import uuid
from datetime import datetime
from aiohttp import web

DB_NAME = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS clicks (id TEXT PRIMARY KEY, timestamp TEXT)"
        )
        conn.commit()

async def register_click(request):
    """
    POST /click
    Registers a user click.
    """
    try:
        click_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                "INSERT INTO clicks (id, timestamp) VALUES (?, ?)", 
                (click_id, timestamp)
            )
            conn.commit()
            
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
        return web.Response(status=400, text="Missing required parameters: date and direction")

    if direction not in ["<", ">", "<=", ">="]:
        return web.Response(status=400, text="Invalid direction. Must be <, >, <=, or >=")

    try:
        # Validate date format (YYYY-MM-DD)
        datetime.strptime(date_str, '%Y-%m-%d')
        
        # We treat the date as the start of that day (00:00:00) for comparison
        filter_date = f"{date_str}T00:00:00"

        with sqlite3.connect(DB_NAME) as conn:
            # Use a parameterized query for the value, but the operator must be handled carefully
            # Since direction is validated against a strict enum, it is safe to interpolate
            query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
            cursor = conn.execute(query, (filter_date,))
            rows = cursor.fetchall()

        if not rows:
            return web.Response(status=404, text="No clicks found")

        clicks = [{"id": row[0], "timestamp": row[1]} for row in rows]
        return web.json_response(clicks)

    except ValueError:
        return web.Response(status=400, text="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        return web.Response(status=400, text=str(e))

async def app_factory():
    app = web.Application()
    app.add_routes([
        web.post('/click', register_click),
        web.get('/clicks', retrieve_clicks),
    ])
    return app

if __name__ == "__main__":
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/click', register_click),
        web.get('/clicks', retrieve_clicks),
    ])
    web.run_app(app, host='0.0.0.0', port=5000)