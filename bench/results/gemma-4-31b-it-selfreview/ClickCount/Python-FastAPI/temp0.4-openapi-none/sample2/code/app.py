import sqlite3
import uuid
from datetime import datetime
from typing import List
from enum import Enum

from fastapi import FastAPI, Query, HTTPException, Response, status
from pydantic import BaseModel
import uvicorn

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def init_db():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS clicks ("
                "id TEXT PRIMARY KEY, "
                "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
            conn.commit()
    except Exception:
        # In a real scenario, log this. Here we ensure the app doesn't crash on startup.
        pass

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
    # Use UTC ISO format for consistency and security against timezone manipulation
    timestamp = datetime.utcnow().isoformat()
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", (click_id, timestamp))
            conn.commit()
        return Response(status_code=status.HTTP_201_CREATED)
    except Exception:
        # Generic error to avoid leaking internal DB details
        raise HTTPException(status_code=400, detail="Invalid request")

@app.get("/clicks", response_model=List[ClickResponse])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks (YYYY-MM-DD)"),
    direction: DirectionEnum = Query(..., description="Specify '<', '<=' or '>' etc.")
):
    """Retrieve clicks before or after a certain date."""
    # Strict validation of date format to prevent any unexpected input reaching the query
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid request")

    # SECURITY FIX: SQL Injection Prevention.
    # We cannot parameterize the operator (e.g., '<', '>') in SQLite.
    # To prevent SQL injection, we MUST NOT use the raw input string.
    # We use the DirectionEnum which restricts the operator to a strict whitelist.
    operator = direction.value
    
    # The query is constructed using a whitelisted operator and a parameterized value.
    query = f"SELECT id, timestamp FROM clicks WHERE timestamp {operator} ?"
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (date,))
            rows = cursor.fetchall()
            
            if not rows:
                # Specification requires 404 when no clicks are found
                raise HTTPException(status_code=404, detail="No clicks found")
            
            return [
                ClickResponse(id=row["id"], timestamp=row["timestamp"]) 
                for row in rows
            ]
    except HTTPException as he:
        raise he
    except Exception:
        # Generic error to avoid leaking internal DB details
        raise HTTPException(status_code=400, detail="Invalid request")

if __name__ == "__main__":
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)