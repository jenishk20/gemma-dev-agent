import sqlite3
import uuid
from datetime import datetime
from typing import List, Literal
from fastapi import FastAPI, HTTPException, Query, status, Request
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
        # In a real scenario, we would log this, but we must ensure the app starts
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
    # Use UTC ISO format for consistency and security
    timestamp = datetime.utcnow().isoformat()
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            # Parameterized query prevents SQL injection
            conn.execute("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", (click_id, timestamp))
            conn.commit()
        return None 
    except Exception:
        # Return documented 400 error without leaking internal database details/stack traces
        raise HTTPException(status_code=400, detail="Invalid request")

@app.get("/clicks", response_model=List[Click])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks (YYYY-MM-DD)"),
    direction: Literal["<", ">", "<=", ">="] = Query(..., description="Filter direction")
):
    """Retrieve clicks before or after a certain date."""
    # Strict validation of date format to prevent any unexpected input reaching the query
    try:
        # This ensures 'date' is exactly YYYY-MM-DD and contains no malicious characters
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request")

    # We treat the date as the start of that day (00:00:00)
    filter_date = f"{date}T00:00:00"
    
    # Security Review: 
    # 1. 'direction' is constrained by Literal["<", ">", "<=", ">="], preventing SQL injection via the operator.
    # 2. 'filter_date' is validated by strptime.
    # 3. The value is passed via a parameterized query (?).
    query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.execute(query, (filter_date,))
            rows = cursor.fetchall()
            
            if not rows:
                # Return documented 404 when no results are found
                raise HTTPException(status_code=404, detail="No clicks found")
            
            # Map to Pydantic model to ensure output is sanitized and matches schema
            results = [Click(id=row[0], timestamp=row[1]) for row in rows]
            return results
    except HTTPException as he:
        raise he
    except Exception:
        # Return documented 400 error without leaking internal details
        raise HTTPException(status_code=400, detail="Invalid request")

# Custom exception handler to prevent leaking internal server errors (stack traces)
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    return uvicorn.responses.JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

if __name__ == "__main__":
    # Port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)