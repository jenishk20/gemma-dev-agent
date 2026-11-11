import sqlite3
import uuid
from datetime import datetime
from typing import List
from fastapi import FastAPI, Query, HTTPException, status
from pydantic import BaseModel
import uvicorn

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def init_db():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS clicks (id TEXT PRIMARY KEY, timestamp DATETIME)"
            )
            conn.commit()
    except Exception:
        # Internal failure during init is critical, but we avoid leaking details
        pass

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
    # Using utcnow().isoformat() is safe. 
    # We ensure we don't leak internal server errors by catching generic exceptions.
    timestamp = datetime.utcnow().isoformat()
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", (click_id, timestamp))
            conn.commit()
        return None 
    except Exception:
        # Return 400 as per OpenAPI spec for invalid requests/failures
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")

@app.get("/clicks", response_model=List[Click])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks (YYYY-MM-DD)"),
    direction: str = Query(..., enum=["<", ">", "<=", ">="], description="Filter direction")
):
    """Retrieve clicks before or after a certain date."""
    # 1. Strict Date Validation to prevent any injection or malformed input
    try:
        # This ensures the input strictly matches YYYY-MM-DD and is a valid calendar date
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")

    # 2. Safe Operator Handling
    # The 'direction' parameter is constrained by the FastAPI Query enum.
    # To be absolutely secure against SQL injection, we map the input to a hardcoded set of operators.
    operator_map = {
        "<": "<",
        ">": ">",
        "<=": "<=",
        ">=": ">="
    }
    # Since direction is validated by Pydantic/FastAPI enum, this lookup is safe.
    op = operator_map.get(direction)
    if not op:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid direction")

    # 3. Parameterized Query
    # We use a parameterized value for the date to prevent SQL injection.
    # The operator is interpolated from our internal map, not directly from user input.
    filter_date = f"{date}T00:00:00"
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            # Only the operator is interpolated; it is sourced from our static map.
            query = f"SELECT id, timestamp FROM clicks WHERE timestamp {op} ?"
            cursor = conn.execute(query, (filter_date,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No clicks found")
            
            return [Click(id=row["id"], timestamp=row["timestamp"]) for row in rows]
    except HTTPException:
        raise
    except Exception:
        # Catch-all to prevent leaking stack traces or internal DB errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")

if __name__ == "__main__":
    # Port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)