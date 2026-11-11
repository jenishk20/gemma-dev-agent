import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional
from enum import Enum

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
import uvicorn

# --- Configuration & Constants ---
DB_FILE = "db.sqlite3"

app = FastAPI(
    title="Click Tracking API",
    version="1.0.0",
    description="API for registering and retrieving user clicks."
)

# --- Database Setup ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS clicks ("
            "id TEXT PRIMARY KEY, "
            "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        conn.commit()

init_db()

# --- Schemas ---
class DirectionEnum(str, Enum):
    LT = "<"
    GT = ">"
    LTE = "<="
    GTE = ">="

class ClickResponse(BaseModel):
    id: str
    timestamp: str

# --- Endpoints ---

@app.post("/click", status_code=status.HTTP_201_CREATED)
async def register_click():
    """
    Endpoint to register a user's click in the database.
    """
    try:
        click_id = str(uuid.uuid4())
        # Use UTC timestamp for consistency
        timestamp = datetime.utcnow().isoformat()
        
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO clicks (id, timestamp) VALUES (?, ?)", 
                (click_id, timestamp)
            )
            conn.commit()
        
        return None # 201 Created with no body as per schema
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid request")

@app.get("/clicks", response_model=List[ClickResponse])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks. Format: YYYY-MM-DD", example="2022-01-01"),
    direction: DirectionEnum = Query(..., description="Specify '<', '<=' or '>' etc. to filter clicks.")
):
    """
    Endpoint to retrieve clicks before or after a certain date.
    """
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # To ensure correct comparison with ISO timestamps in SQLite, 
    # we treat the input date as the start of that day.
    filter_date = f"{date} 00:00:00"
    
    # Use a parameterized query to prevent SQL injection
    # Note: The operator (direction) is validated by the Enum, so it is safe to interpolate
    # but we use the enum value explicitly.
    op = direction.value
    query = f"SELECT id, timestamp FROM clicks WHERE timestamp {op} ?"

    try:
        with get_db_connection() as conn:
            cursor = conn.execute(query, (filter_date,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No clicks found")
            
            return [
                ClickResponse(id=row["id"], timestamp=row["timestamp"]) 
                for row in rows
            ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid request")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)