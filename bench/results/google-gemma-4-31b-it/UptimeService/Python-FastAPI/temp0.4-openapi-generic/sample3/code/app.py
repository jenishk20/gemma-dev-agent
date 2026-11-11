import os
import sqlite3
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# --- Database Setup ---
DB_PATH = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
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

# --- Models ---
class HeartbeatRequest(BaseModel):
    serviceId: str = Field(..., description="The unique identifier of the service.")
    token: str = Field(..., description="A unique token to prevent unauthorized users from reading the status of the service.")

class TokenRequest(BaseModel):
    token: str = Field(..., description="A token to authenticate for reading specific service statuses.")

class ServiceStatus(BaseModel):
    serviceId: str
    lastNotification: str

# --- App Initialization ---
app = FastAPI(
    title="Service Monitoring API",
    version="1.0.0",
    description="API for monitoring the status of services."
)

@app.on_event("startup")
async def startup_event():
    init_db()

# --- Endpoints ---

@app.post("/heartbeat", status_code=status.HTTP_200_OK)
async def register_heartbeat(payload: HeartbeatRequest):
    """
    Accepts a request to signify that a specific service is still alive.
    """
    try:
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            # Use UPSERT logic to update the token and timestamp for the serviceId
            conn.execute(
                "INSERT INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?) "
                "ON CONFLICT(serviceId) DO UPDATE SET token=excluded.token, lastNotification=excluded.lastNotification",
                (payload.serviceId, payload.token, now)
            )
            conn.commit()
        return {}
    except Exception as e:
        # Log the error in a real scenario
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/services", response_model=List[ServiceStatus])
async def get_services_overview(payload: TokenRequest):
    """
    Provides an overview of registered services and their last notification date, 
    where the token of this request matches the token sent with the service request.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                "SELECT serviceId, lastNotification FROM services WHERE token = ?", 
                (payload.token,)
            )
            rows = cursor.fetchall()
            
            return [
                ServiceStatus(serviceId=row[0], lastNotification=row[1]) 
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error.")

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)