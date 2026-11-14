import os
import sqlite3
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import uvicorn

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
DB_PATH = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS services (
                serviceId TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                lastNotification TEXT NOT NULL
            )
        """)
        conn.commit()

def update_heartbeat(service_id: str, token: str):
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        # We use REPLACE to handle both insert and update (upsert)
        conn.execute(
            "INSERT OR REPLACE INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)",
            (service_id, token, now)
        )
        conn.commit()

def get_services_by_token(token: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT serviceId, lastNotification FROM services WHERE token = ?", 
            (token,)
        )
        return cursor.fetchall()

# --- App Initialization ---
app = FastAPI(title="Service Monitoring API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/heartbeat", status_code=status.HTTP_200_OK)
async def register_heartbeat(payload: HeartbeatRequest):
    try:
        update_heartbeat(payload.serviceId, payload.token)
        return {} # 200 OK
    except Exception as e:
        # In a real scenario, we'd log the error
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/services", response_model=List[ServiceStatus], status_code=status.HTTP_200_OK)
async def get_services(payload: TokenRequest):
    try:
        rows = get_services_by_token(payload.token)
        return [ServiceStatus(serviceId=row[0], lastNotification=row[1]) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error.")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)