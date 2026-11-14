import sqlite3
import uuid
from datetime import datetime
from typing import List, Literal
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
import uvicorn

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS clicks (id TEXT PRIMARY KEY, timestamp DATETIME)"
        )
        conn.commit()

# --- Models ---
class Click(BaseModel):
    id: str
    timestamp: str

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
        return None # OpenAPI schema says 201, no body specified for success
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/clicks", response_model=List[Click])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks (YYYY-MM-DD)"),
    direction: Literal["<", ">", "<=", ">="] = Query(..., description="Filter direction")
):
    """Retrieve clicks before or after a certain date."""
    # Validate date format simply
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # We treat the date as the start of that day (00:00:00)
    filter_date = f"{date}T00:00:00"
    
    # Use a parameterized query to prevent SQL injection
    # Note: direction is validated by Literal, so it's safe to interpolate
    query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.execute(query, (filter_date,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No clicks found")
            
            results = [Click(id=row[0], timestamp=row[1]) for row in rows]
            return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)