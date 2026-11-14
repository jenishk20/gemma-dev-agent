import os
import sqlite3
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# --- Configuration ---
DB_PATH = "db.sqlite3"
# APP_SECRET is provided via env variable as per requirements, 
# though not explicitly used for logic in this specific schema's auth (which uses token-based matching).
APP_SECRET = os.getenv("APP_SECRET", "default_secret")

app = FastAPI(title="Service Monitoring API", version="1.0.0")

# --- Database Setup ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS services (
                serviceId TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                lastNotification DATETIME NOT NULL
            )
        """)
        conn.commit()

init_db()

# --- Pydantic Models ---
class HeartbeatRequest(BaseModel):
    serviceId: str = Field(..., description="The unique identifier of the service.")
    token: str = Field(..., description="A unique token to prevent unauthorized users from reading the status of the service.")

class ServiceOverviewRequest(BaseModel):
    token: str = Field(..., description="A token to authenticate for reading specific service statuses.")

class ServiceStatus(BaseModel):
    serviceId: str
    lastNotification: str

# --- Endpoints ---

@app.post("/heartbeat", status_code=status.HTTP_200_OK)
async def register_heartbeat(payload: HeartbeatRequest):
    """
    Accepts a request to signify that a specific service is still alive.
    """
    try:
        now = datetime.utcnow().isoformat()
        with get_db_connection() as conn:
            # Use UPSERT logic (INSERT or REPLACE) to update the heartbeat and token
            conn.execute(
                "INSERT OR REPLACE INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)",
                (payload.serviceId, payload.token, now)
            )
            conn.commit()
        return {} # Return empty body as per 200 response description
    except Exception as e:
        # Log error here in a real scenario
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@app.post("/services", response_model=List[ServiceStatus])
async def get_services_overview(payload: ServiceOverviewRequest):
    """
    Provides an overview of registered services and their last notification date, 
    where the token of this request matches the token sent with the service request.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT serviceId, lastNotification FROM services WHERE token = ?", 
                (payload.token,)
            )
            rows = cursor.fetchall()
            
            results = [
                ServiceStatus(serviceId=row["serviceId"], lastNotification=row["lastNotification"]) 
                for row in rows
            ]
            return results
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

if __name__ == "__main__":
    import uvicorn
    # Start webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)