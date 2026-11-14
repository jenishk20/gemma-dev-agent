import os
import sqlite3
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Initialize FastAPI app
app = FastAPI(title="Service Monitoring API", version="1.0.0")

DB_FILE = "db.sqlite3"

# Database initialization
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS services (
                serviceId TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                lastNotification TEXT NOT NULL
            )
            """
        )
        conn.commit()

init_db()

# Request/Response Models
class HeartbeatRequest(BaseModel):
    serviceId: str = Field(..., description="The unique identifier of the service.")
    token: str = Field(..., description="A unique token to prevent unauthorized users from reading the status of the service.")

class TokenRequest(BaseModel):
    token: str = Field(..., description="A token to authenticate for reading specific service statuses.")

class ServiceStatus(BaseModel):
    serviceId: str
    lastNotification: str

# Endpoints
@app.post("/heartbeat", status_code=status.HTTP_200_OK)
async def register_heartbeat(payload: HeartbeatRequest):
    """
    Accepts a request to signify that a specific service is still alive.
    """
    try:
        now = datetime.utcnow().isoformat() + "Z"
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Check if service exists to update token or just insert/replace
            cursor.execute(
                "INSERT OR REPLACE INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)",
                (payload.serviceId, payload.token, now)
            )
            conn.commit()
        return None # 200 OK
    except Exception as e:
        # Log error here if needed
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/services", response_model=List[ServiceStatus])
async def get_services(payload: TokenRequest):
    """
    Provides an overview of registered services and their last notification date, 
    where the token of this request matches the token sent with the service request.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT serviceId, lastNotification FROM services WHERE token = ?", (payload.token,))
            rows = cursor.fetchall()
            
            results = [
                ServiceStatus(serviceId=row["serviceId"], lastNotification=row["lastNotification"]) 
                for row in rows
            ]
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error.")

if __name__ == "__main__":
    import uvicorn
    # Start server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)