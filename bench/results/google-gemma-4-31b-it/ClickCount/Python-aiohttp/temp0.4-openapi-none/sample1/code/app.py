import os
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

async def handle_register_click(request):
    """
    POST /click
    Registers a user's click in the database.
    """
    try:
        click_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO clicks (id, timestamp) VALUES (?, ?)', (click_id, timestamp))
        conn.commit()
        conn.close()
        
        return web.Response(status=201)
    except Exception:
        return web.Response(status=400, text="Invalid request")

async def handle_retrieve_clicks(request):
    """
    GET /clicks
    Retrieves clicks based on date and direction filter.
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
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # We use a parameterized query for the date, but the operator must be hardcoded 
        # from the validated enum list to prevent SQL injection.
        query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
        cursor.execute(query, (date_str,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return web.Response(status=404, text="No clicks found")

        clicks = [{"id": row[0], "timestamp": row[1]} for row in rows]
        return web.json_response(clicks)
        
    except ValueError:
        return web.Response(status=400, text="Invalid date format. Expected YYYY-MM-DD")
    except Exception as e:
        return web.Response(status=400, text=str(e))

async def init_app():
    """Initialize the aiohttp application."""
    app = web.Application()
    app.add_routes([
        web.post('/click', handle_register_click),
        web.get('/clicks', handle_retrieve_clicks),
    ])
    return app

if __name__ == "__main__":
    # Initialize DB before starting server
    init_db()
    
    app = web.Application()
    app.add_routes([
        web.post('/click', handle_register_click),
        web.get('/clicks', handle_retrieve_clicks),
    ])
    
    web.run_app(app, host='0.0.0.0', port=5000)