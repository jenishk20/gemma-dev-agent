import sqlite3
import uuid
from datetime import datetime
from typing import List, Literal
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
import uvicorn

# --- Database Setup ---
DB_PATH = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS clicks ("
            "id TEXT PRIMARY KEY, "
            "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        conn.commit()

init_db()

# --- Models ---
class ClickResponse(BaseModel):
    id: str = Field(..., description="The unique identifier for the click.")
    timestamp: str = Field(..., description="The timestamp of the click.")

# --- App Initialization ---
app = FastAPI(
    title="Click Tracking API",
    version="1.0.0",
    description="API for registering and retrieving user clicks."
)

@app.post("/click", status_code=status.HTTP_201_CREATED)
async def register_click():
    """
    Endpoint to register a user's click in the database.
    """
    try:
        click_id = str(uuid.uuid4())
        # Using ISO format for consistency with OpenAPI date-time
        timestamp = datetime.utcnow().isoformat()
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO clicks (id, timestamp) VALUES (?, ?)", 
                (click_id, timestamp)
            )
            conn.commit()
        
        return None # OpenAPI says 201 description, no body specified for response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

@app.get("/clicks", response_model=List[ClickResponse])
async def retrieve_clicks(
    date: str = Query(..., description="The date to filter clicks. Format: YYYY-MM-DD"),
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

    # We use a parameterized query to prevent SQL injection.
    # Since the operator (direction) is from a strict Enum (Literal), 
    # we can safely interpolate it into the query string.
    query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # SQLite handles ISO strings for date comparisons
            cursor = conn.execute(query, (date,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No clicks found")
            
            results = [{"id": row[0], "timestamp": row[1]} for row in rows]
            return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)