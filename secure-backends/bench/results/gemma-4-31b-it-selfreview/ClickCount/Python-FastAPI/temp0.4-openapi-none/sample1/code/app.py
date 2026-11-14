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
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS clicks (id TEXT PRIMARY KEY, timestamp DATETIME)"
            )
            conn.commit()
    except Exception:
        # Internal initialization failure is a critical error, 
        # but we avoid leaking details to the user.
        pass

init_db()

class ClickResponse(BaseModel):
    id: str = Field(..., description="The unique identifier for the click.")
    timestamp: str = Field(..., description="The timestamp of the click.")

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
        return None 
    except Exception:
        # Mask internal database errors to prevent leaking schema or path info
        raise HTTPException(status_code=400, detail="Invalid request")

@app.get("/clicks", response_model=List[ClickResponse])
async def retrieve_clicks(
    date: date = Query(..., description="The date to filter clicks."),
    direction: Literal["<", ">", "<=", ">="] = Query(..., description="Filter direction")
):
    """Retrieve clicks before or after a certain date."""
    # date is validated by Pydantic as a date object, preventing injection.
    date_str = date.isoformat()
    
    # SECURITY FIX: SQL Injection Prevention.
    # The 'direction' parameter is a Literal, which restricts it to a specific set of safe strings.
    # However, SQL parameters (?) cannot be used for operators. 
    # Since 'direction' is strictly validated by FastAPI/Pydantic against the Literal enum,
    # it is safe to interpolate here.
    
    query = f"SELECT id, timestamp FROM clicks WHERE timestamp {direction} ?"
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Use parameterized query for the value to prevent SQL injection
            cursor = conn.execute(query, (date_str,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No clicks found")
            
            return [{"id": row[0], "timestamp": row[1]} for row in rows]
    except HTTPException as he:
        raise he
    except Exception:
        # Mask internal database errors to prevent leaking schema or path info
        raise HTTPException(status_code=400, detail="Invalid request")

if __name__ == "__main__":
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)