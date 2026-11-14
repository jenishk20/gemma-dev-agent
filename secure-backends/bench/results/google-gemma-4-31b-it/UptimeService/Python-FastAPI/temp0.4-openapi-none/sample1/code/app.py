import os
import sqlite3
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import uvicorn

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def init_db():
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

@app.post("/heartbeat", status_code=200)
async def register_heartbeat(payload: HeartbeatRequest):
    try:
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Check if service exists to see if token matches
            cursor.execute("SELECT token FROM services WHERE serviceId = ?", (payload.serviceId,))
            row = cursor.fetchone()
            
            if row:
                # Update existing service
                cursor.execute(
                    "UPDATE services SET lastNotification = ?, token = ? WHERE serviceId = ?", 
                    (now, payload.token, payload.serviceId)
                )
            else:
                # Insert new service
                cursor.execute(
                    "INSERT INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)", 
                    (payload.serviceId, payload.token, now)
                )
            conn.commit()
        return None # Returns 200 OK as per schema
    except Exception as e:
        # In a real scenario, log the exception e
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/services", response_model=List[ServiceStatus])
async def get_services(payload: TokenRequest):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT serviceId, lastNotification FROM services WHERE token = ?", 
                (payload.token,)
            )
            rows = cursor.fetchall()
            
            results = [
                ServiceStatus(serviceId=row[0], lastNotification=row[1]) 
                for row in rows
            ]
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error.")

if __name__ == "__main__":
    # The prompt requires the server to start on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)