import sqlite3
import uuid
from datetime import datetime
from typing import List
from enum import Enum

from fastapi import FastAPI, Query, HTTPException, status
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Click Tracking API")

DB_PATH = "db.sqlite3"

# --- Database Setup ---
def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS clicks (id TEXT PRIMARY KEY, timestamp DATETIME)"
            )
            conn.commit()
    except Exception:
        # In a production environment, this would be logged.
        pass

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
    # Use UTC timestamp for consistency and security
    timestamp = datetime.utcnow().isoformat()
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", (click_id, timestamp))
            conn.commit()
    except Exception:
        # Return 400 as per OpenAPI spec for invalid requests/internal failures during registration
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")
    
    return None

@app.get("/clicks", response_model=List[Click])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks (YYYY-MM-DD)"),
    direction: DirectionEnum = Query(..., description="Specify '<', '<=' or '>' etc.")
):
    """Retrieve clicks before or after a certain date."""
    # Strict validation of date format to prevent any unexpected input reaching the query
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD")

    # The 'direction' is strictly validated by the DirectionEnum (FastAPI/Pydantic), 
    # preventing SQL injection via the operator.
    # We use a whitelist of operators from the Enum.
    operator = direction.value
    filter_date = f"{date}T00:00:00"
    
    # Since the operator cannot be parameterized in SQLite, we use the validated Enum value.
    # The value is guaranteed to be one of ['<', '>', '<=', '>='].
    query = f"SELECT id, timestamp FROM clicks WHERE timestamp {operator} ?"
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (filter_date,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No clicks found")
            
            return [Click(id=row["id"], timestamp=row["timestamp"]) for row in rows]
    except HTTPException as he:
        raise he
    except Exception:
        # Catch-all to prevent leaking internal stack traces or DB errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")

if __name__ == "__main__":
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)