import os
import sqlite3
import secrets
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field

# --- Configuration ---
DB_PATH = "db.sqlite3"

app = FastAPI(
    title="Service Monitoring API",
    version="1.0.0",
    description="API for monitoring the status of services."
)

# --- Database Setup ---
def init_db():
    # Using a context manager for the connection
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

init_db()

# --- Models ---
class HeartbeatRequest(BaseModel):
    serviceId: str = Field(..., description="The unique identifier of the service.")
    token: str = Field(..., description="A unique token to prevent unauthorized users from reading the status of the service.")

class TokenRequest(BaseModel):
    token: str = Field(..., description="A token to authenticate for reading specific service statuses.")

class ServiceStatus(BaseModel):
    serviceId: str
    lastNotification: str

# --- Security Helpers ---
def secure_compare(a: str, b: str) -> bool:
    """Constant-time comparison to prevent timing attacks on tokens."""
    return secrets.compare_digest(a, b)

# --- Endpoints ---

@app.post("/heartbeat", status_code=status.HTTP_200_OK)
async def register_heartbeat(payload: HeartbeatRequest):
    """
    Accepts a request to signify that a specific service is still alive.
    """
    # Input validation: Ensure IDs and tokens aren't excessively large to prevent resource exhaustion
    if len(payload.serviceId) > 255 or len(payload.token) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request payload.")

    try:
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            # Use parameterized queries to prevent SQL Injection
            conn.execute(
                "INSERT OR REPLACE INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)",
                (payload.serviceId, payload.token, now)
            )
            conn.commit()
        return {"message": "Heartbeat registered successfully."}
    except Exception:
        # Catch-all to prevent leaking stack traces/internal details
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@app.post("/services", response_model=List[ServiceStatus])
async def get_services_overview(payload: TokenRequest):
    """
    Provides an overview of registered services and their last notification date, 
    where the token of this request matches the token sent with the service request.
    """
    if len(payload.token) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request payload.")

    try:
        results = []
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Parameterized query to prevent SQL Injection
            cursor.execute(
                "SELECT serviceId, lastNotification, token FROM services"
            )
            rows = cursor.fetchall()
            
            # Use constant-time comparison for token verification to prevent timing attacks
            # and ensure the caller only sees services they are authorized for.
            for row in rows:
                if secure_compare(row["token"], payload.token):
                    results.append(
                        ServiceStatus(
                            serviceId=row["serviceId"], 
                            lastNotification=row["lastNotification"]
                        )
                    )
        return results
    except Exception:
        # Catch-all to prevent leaking stack traces/internal details
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

# Middleware to limit request body size to prevent resource exhaustion (DoS)
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Limit request body to 1MB
    MAX_SIZE = 1024 * 1024 
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Request body too large")
    return await call_next(request)

if __name__ == "__main__":
    import uvicorn
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)