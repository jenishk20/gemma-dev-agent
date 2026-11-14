import os
import sqlite3
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# --- Configuration ---
DB_PATH = "db.sqlite3"
# APP_SECRET is available via os.environ.get("APP_SECRET") if needed for logic, 
# though the schema relies on token-based matching.

app = FastAPI(
    title="Service Monitoring API",
    version="1.0.0",
    description="API for monitoring the status of services."
)

# --- Database Setup ---
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

# --- Endpoints ---

@app.post("/heartbeat", status_code=status.HTTP_200_OK)
async def register_heartbeat(payload: HeartbeatRequest):
    """
    Accepts a request to signify that a specific service is still alive.
    """
    try:
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Check if service exists to update token or just insert/replace
            cursor.execute(
                "INSERT OR REPLACE INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?)",
                (payload.serviceId, payload.token, now)
            )
            conn.commit()
        return {"message": "Heartbeat registered successfully."}
    except Exception as e:
        # In a real app, we'd log this
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/services", response_model=List[ServiceStatus])
async def get_services_overview(payload: TokenRequest):
    """
    Provides an overview of registered services and their last notification date, 
    where the token of this request matches the token sent with the service request.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT serviceId, lastNotification FROM services WHERE token = ?", 
                (payload.token,)
            )
            rows = cursor.fetchall()
            
            return [
                ServiceStatus(serviceId=row["serviceId"], lastNotification=row["lastNotification"]) 
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error.")

if __name__ == "__main__":
    import uvicorn
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)