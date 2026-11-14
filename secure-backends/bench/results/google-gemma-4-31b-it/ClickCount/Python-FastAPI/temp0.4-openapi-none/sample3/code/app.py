import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException, status
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
        return None # 201 Created usually returns no body or a confirmation
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/clicks", response_model=List[Click])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks (YYYY-MM-DD)"),
    direction: str = Query(..., enum=["<", ">", "<=", ">="], description="Filter direction")
):
    """Retrieve clicks before or after a certain date."""
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # We compare the timestamp string. Since ISO format is used, 
    # lexicographical comparison works for dates.
    # We append 'T00:00:00' to the date to make it a valid timestamp for comparison.
    filter_date = f"{date}T00:00:00"
    
    # Map the direction to a SQL operator
    # Note: In a real app, we'd use parameterized queries for values, 
    # but the operator itself cannot be parameterized in SQLite.
    # Since we use an enum in the Query, it is safe from SQL injection.
    operator_map = {
        "<": "<",
        ">": ">",
        "<=": "<=",
        ">=": ">="
    }
    op = operator_map[direction]

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"SELECT id, timestamp FROM clicks WHERE timestamp {op} ?", (filter_date,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No clicks found")
            
            return [Click(id=row["id"], timestamp=row["timestamp"]) for row in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)