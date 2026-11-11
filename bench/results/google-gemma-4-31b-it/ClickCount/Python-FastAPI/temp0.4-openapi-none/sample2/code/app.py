import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional
from enum import Enum

from fastapi import FastAPI, Query, HTTPException, Response, status
from pydantic import BaseModel, Field
import uvicorn

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS clicks ("
            "id TEXT PRIMARY KEY, "
            "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        conn.commit()

# --- Schemas ---
class ClickResponse(BaseModel):
    id: str
    timestamp: str

class DirectionEnum(str, Enum):
    lt = "<"
    gt = ">"
    lte = "<="
    gte = ">="

# --- App Initialization ---
app = FastAPI(title="Click Tracking API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    init_db()

# --- Endpoints ---

@app.post("/click", status_code=status.HTTP_201_CREATED)
async def register_click():
    """Register a user's click in the database."""
    click_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", (click_id, timestamp))
            conn.commit()
        return Response(status_code=status.HTTP_201_CREATED)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/clicks", response_model=List[ClickResponse])
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

    # Map the enum value to the SQL operator
    operator = direction.value
    
    # SQLite uses 'YYYY-MM-DD HH:MM:SS' or ISO8601. 
    # We compare the timestamp column with the provided date.
    # Since the date provided is YYYY-MM-DD, it effectively represents 00:00:00 of that day.
    query = f"SELECT id, timestamp FROM clicks WHERE timestamp {operator} ?"
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (date,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No clicks found")
            
            return [
                ClickResponse(id=row["id"], timestamp=row["timestamp"]) 
                for row in rows
            ]
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)