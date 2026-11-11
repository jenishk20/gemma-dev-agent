import os
import sqlite3
import secrets
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

# --- Models ---

class HeartbeatRequest(BaseModel):
    serviceId: str = Field(..., description="The unique identifier of the service.")
    token: str = Field(..., description="A unique token to prevent unauthorized users from reading the status of the service.")

class TokenRequest(BaseModel):
    token: str = Field(..., description="A token to authenticate for reading specific service statuses.")

class ServiceStatus(BaseModel):
    serviceId: str
    lastNotification: str

# --- Database Logic ---

# Hardcoded DB path to prevent path traversal
DB_PATH = "db.sqlite3"

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS heartbeats (
                    serviceId TEXT PRIMARY KEY,
                    token TEXT NOT NULL,
                    lastNotification TEXT NOT NULL
                )
            """)
            conn.commit()
    except Exception:
        # In a production environment, this would be logged
        pass

# --- App Initialization ---

app = FastAPI(
    title="Service Monitoring API",
    version="1.0.0",
    description="API for monitoring the status of services."
)

@app.on_event("startup")
async def startup_event():
    init_db()

# --- Security Helpers ---

def secure_compare(a: str, b: str) -> bool:
    """Constant-time comparison to prevent timing attacks on tokens."""
    return secrets.compare_digest(a, b)

# --- Endpoints ---

@app.post("/heartbeat", status_code=200)
async def register_heartbeat(payload: HeartbeatRequest):
    """
    Register a heartbeat for a service.
    """
    # Input validation: Ensure IDs and tokens aren't excessively large to prevent resource exhaustion
    if len(payload.serviceId) > 255 or len(payload.token) > 255:
        raise HTTPException(status_code=400, detail="Invalid request payload.")

    try:
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Parameterized query prevents SQL Injection
            cursor.execute(
                "INSERT OR REPLACE INTO heartbeats (serviceId, token, lastNotification) VALUES (?, ?, ?)",
                (payload.serviceId, payload.token, now)
            )
            conn.commit()
        return None
    except Exception:
        # Generic error to prevent leaking internal stack traces/DB details
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/services", response_model=List[ServiceStatus])
async def get_services(payload: TokenRequest):
    """
    Get overview of registered services.
    """
    if len(payload.token) > 255:
        raise HTTPException(status_code=400, detail="Invalid request payload.")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Parameterized query prevents SQL Injection
            cursor.execute(
                "SELECT serviceId, lastNotification FROM heartbeats WHERE token = ?",
                (payload.token,)
            )
            rows = cursor.fetchall()
            
            # We use the token provided in the request to filter the database.
            # The database query itself handles the authorization logic: 
            # only services registered with that specific token are returned.
            results = [
                ServiceStatus(serviceId=row[0], lastNotification=row[1]) 
                for row in rows
            ]
            return results
    except Exception:
        # Generic error to prevent leaking internal stack traces/DB details
        raise HTTPException(status_code=500, detail="Internal server error.")

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)