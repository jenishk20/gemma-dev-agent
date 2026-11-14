import sqlite3
import uuid
from datetime import datetime
from typing import List, Literal
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
import uvicorn

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS clicks (id TEXT PRIMARY KEY, timestamp DATETIME)"
        )
        conn.commit()

# --- Models ---
class Click(BaseModel):
    id: str = Field(..., description="The unique identifier for the click.")
    timestamp: str = Field(..., description="The timestamp of the click.")

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
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO clicks (id, timestamp) VALUES (?, ?)", 
                (click_id, timestamp)
            )
            conn.commit()
        return None # OpenAPI schema says 201, no specific body required for POST
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

@app.get("/clicks", response_model=List[Click])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks (YYYY-MM-DD).", example="2022-01-01"),
    direction: Literal["<", ">", "<=", ">="] = Query(..., description="Filter direction")
):
    """Retrieve clicks before or after a certain date."""
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # To prevent SQL injection, we only allow the enum values for 'direction' 
    # and use parameterized queries for the date value.
    # Since 'direction' is an operator, it cannot be parameterized in SQLite.
    # We use the Literal type hint and a whitelist check to ensure safety.
    allowed_operators = {"<", ">", "<=", ">="}
    if direction not in allowed_operators:
        raise HTTPException(status_code=400, detail="Invalid direction operator")

    try:
        with get_db_connection() as conn:
            # We construct the query using the validated operator and parameterized date
            query = f"SELECT id, timestamp FROM clicks WHERE date(timestamp) {direction} ?"
            cursor = conn.execute(query, (date,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No clicks found")
            
            return [Click(id=row["id"], timestamp=row["timestamp"]) for row in rows]
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)