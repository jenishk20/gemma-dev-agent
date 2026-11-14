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
            "CREATE TABLE IF NOT EXISTS clicks ("
            "id TEXT PRIMARY KEY, "
            "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
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
    """
    Endpoint to register a user's click in the database.
    """
    try:
        click_id = str(uuid.uuid4())
        # We use current UTC time for the timestamp
        timestamp = datetime.utcnow().isoformat()
        
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", (click_id, timestamp))
            conn.commit()
        
        return None # 201 Created with no content as per schema implicit response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

@app.get("/clicks", response_model=List[Click])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks (YYYY-MM-DD)"),
    direction: Literal["<", ">", "<=", ">="] = Query(..., description="Filter direction")
):
    """
    Endpoint to retrieve clicks before or after a certain date.
    """
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # To ensure correct comparison in SQLite, we treat the date as the start of that day
    # SQLite stores dates as strings. We compare the timestamp column with the provided date.
    # Since timestamps are ISO format (YYYY-MM-DDTHH:MM:SS), 
    # comparing '2022-01-01' with '2022-01-01T10:00:00' works lexicographically.
    
    # Use a whitelist for the operator to prevent SQL injection, 
    # though Literal already restricts input at the FastAPI layer.
    allowed_operators = {"<", ">", "<=", ">="}
    if direction not in allowed_operators:
        raise HTTPException(status_code=400, detail="Invalid direction operator")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            # We use f-string for the operator because it cannot be parameterized in SQL
            # But we have strictly validated 'direction' against a set of 4 constants.
            query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
            cursor = conn.execute(query, (date,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No clicks found")
            
            results = []
            for row in rows:
                results.append(Click(id=row[0], timestamp=row[1]))
            
            return results
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    # Run the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)