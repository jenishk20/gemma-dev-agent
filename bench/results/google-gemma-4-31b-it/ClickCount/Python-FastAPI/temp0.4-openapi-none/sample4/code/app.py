import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional
from enum import Enum

from fastapi import FastAPI, Query, HTTPException, status
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Click Tracking API")

DB_PATH = "db.sqlite3"

# --- Database Setup ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS clicks (id TEXT PRIMARY KEY, timestamp DATETIME)"
        )
        conn.commit()

init_db()

# --- Models ---
class Click(BaseModel):
    id: str
    timestamp: str

class DirectionEnum(str, Enum):
    lt = "<"
    gt = ">"
    lte = "<="
    gte = ">="

# --- Endpoints ---

@app.post("/click", status_code=status.HTTP_201_CREATED)
async def register_click():
    """Register a user's click in the database."""
    click_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", (click_id, timestamp))
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    
    return None

@app.get("/clicks", response_model=List[Click])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks (YYYY-MM-DD)"),
    direction: DirectionEnum = Query(..., description="Specify '<', '<=' or '>' etc.")
):
    """Retrieve clicks before or after a certain date."""
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # SQLite stores dates as strings. We compare the timestamp column with the provided date.
    # Since timestamps are ISO format, simple string comparison works for date filtering.
    # We append ' 00:00:00' to the date to ensure it's treated as the start of that day.
    filter_date = f"{date}T00:00:00"
    
    query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction.value} ?"
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (filter_date,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No clicks found")
            
            return [Click(id=row["id"], timestamp=row["timestamp"]) for row in rows]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)