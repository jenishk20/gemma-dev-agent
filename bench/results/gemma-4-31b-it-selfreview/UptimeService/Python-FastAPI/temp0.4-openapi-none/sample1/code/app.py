import os
import sqlite3
import hmac
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import uvicorn

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def init_db():
    # Ensure the database file is created in the current working directory
    # and not influenced by user input.
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS services (
                serviceId TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                lastNotification TEXT NOT NULL
            )
        """)
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

# --- App Initialization ---
app = FastAPI(title="Service Monitoring API", version="1.0.0", description="API for monitoring the status of services.")

def secure_compare(a: str, b: str) -> bool:
    """
    Constant-time comparison to prevent timing attacks on tokens.
    """
    return hmac.compare_digest(a.encode(), b.encode())

@app.post("/heartbeat", status_code=200)
async def register_heartbeat(payload: HeartbeatRequest):
    try:
        # Bound input size implicitly handled by Pydantic/FastAPI, 
        # but we ensure we use parameterized queries to prevent SQL injection.
        now = datetime.utcnow().isoformat()
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT token FROM services WHERE serviceId = ?", (payload.serviceId,))
            row = cursor.fetchone()
            
            if row:
                # Security: If service exists, verify the token provided matches the stored token
                # to prevent an attacker from hijacking a serviceId by simply guessing it.
                stored_token = row[0]
                if not secure_compare(stored_token, payload.token):
                    # The schema specifies 400 for invalid request payload.
                    # Unauthorized token for a known service is treated as an invalid request.
                    raise HTTPException(status_code=400, detail="Invalid token for the provided serviceId.")
                
                cursor.execute(
                    "UPDATE services SET lastNotification = ? WHERE serviceId = ?", 
                    (now, payload.serviceId)
                )
            else:
                # Insert new service
                cursor.execute(
                    "INSERT INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)", 
                    (payload.serviceId, payload.token, now)
                )
            conn.commit()
        return None
    except HTTPException as he:
        raise he
    except Exception:
        # Error handling: Catch all to prevent leaking stack traces/internal details.
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/services", response_model=List[ServiceStatus])
async def get_services(payload: TokenRequest):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Parameterized query prevents SQL injection.
            cursor.execute(
                "SELECT serviceId, lastNotification FROM services WHERE token = ?", 
                (payload.token,)
            )
            rows = cursor.fetchall()
            
            # The schema requires returning all services registered with the given token.
            # We use a list comprehension to map the database rows to the Pydantic model.
            results = [
                ServiceStatus(serviceId=row[0], lastNotification=row[1]) 
                for row in rows
            ]
            return results
    except Exception:
        # Error handling: Catch all to prevent leaking stack traces/internal details.
        raise HTTPException(status_code=500, detail="Internal server error.")

if __name__ == "__main__":
    # Start webserver on 0.0.0.0:5000 as requested.
    uvicorn.run(app, host="0.0.0.0", port=5000)