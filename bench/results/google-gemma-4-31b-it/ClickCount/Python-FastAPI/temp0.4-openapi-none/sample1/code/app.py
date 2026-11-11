import sqlite3
import uuid
from datetime import datetime, date
from typing import List, Literal
from fastapi import FastAPI, Query, HTTPException, status
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Click Tracking API", version="1.0.0")

DB_PATH = "db.sqlite3"

# Database initialization
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS clicks (id TEXT PRIMARY KEY, timestamp DATETIME)"
        )
        conn.commit()

init_db()

class ClickResponse(BaseModel):
    id: str = Field(..., description="The unique identifier for the click.")
    timestamp: str = Field(..., description="The timestamp of the click.")

@app.post("/click", status_code=status.HTTP_201_CREATED)
async def register_click():
    """Register a user's click in the database."""
    click_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO clicks (id, timestamp) VALUES (?, ?)", (click_id, timestamp))
            conn.commit()
        return None # 201 No Content / Success
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

@app.get("/clicks", response_model=List[ClickResponse])
async def retrieve_clicks(
    date: date = Query(..., description="The date to filter clicks."),
    direction: Literal["<", ">", "<=", ">="] = Query(..., description="Filter direction")
):
    """Retrieve clicks before or after a certain date."""
    # Convert date object to string for SQL comparison (YYYY-MM-DD)
    date_str = date.isoformat()
    
    # Map direction to SQL operator
    # Note: SQLite handles ISO8601 strings for comparison
    query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(query, (date_str,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No clicks found")
            
            return [{"id": row[0], "timestamp": row[1]} for row in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)