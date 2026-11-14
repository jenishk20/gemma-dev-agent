import sqlite3
import uuid
from datetime import datetime
from typing import List, Literal
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Click Tracking API", version="1.0.0")

DB_PATH = "db.sqlite3"

# --- Database Setup ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS clicks ("
            "id TEXT PRIMARY KEY, "
            "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.commit()

init_db()

# --- Schemas ---
class Click(BaseModel):
    id: str
    timestamp: str

# --- Endpoints ---

@app.post("/click", status_code=status.HTTP_201_CREATED)
async def register_click():
    """Register a user's click in the database."""
    click_id = str(uuid.uuid4())
    # Using UTC timestamp for consistency
    timestamp = datetime.utcnow().isoformat()
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO clicks (id, timestamp) VALUES (?, ?)", 
                (click_id, timestamp)
            )
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return None # 201 Created with no body as per schema

@app.get("/clicks", response_model=List[Click])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks (YYYY-MM-DD)"),
    direction: Literal["<", ">", "<=", ">="] = Query(..., description="Filter direction")
):
    """Retrieve clicks before or after a certain date."""
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # We treat the date as the start of that day (00:00:00)
    filter_date = f"{date} 00:00:00"
    
    # Use parameterized queries to prevent SQL injection
    # Note: The operator cannot be parameterized in SQLite, but we use a Literal 
    # in the FastAPI Query to strictly validate that 'direction' is one of the 4 allowed strings.
    query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (filter_date,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No clicks found")
            
            return [Click(id=row["id"], timestamp=row["timestamp"]) for row in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)