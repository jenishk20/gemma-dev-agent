import os
import sqlite3
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from fastapi.responses import JSONResponse

# Configuration
DB_PATH = "db.sqlite3"
# APP_SECRET is provided via env, though not used for JWTs in this specific API spec
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")

# Password hashing setup: bcrypt is a strong salted KDF
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="InviteAPI")

# --- Database Setup ---

def get_db():
    # Using a context manager for the connection to ensure it closes
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        # Table for invitations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                invite_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)
        # Table for users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        conn.commit()

init_db()

# --- Pydantic Models ---
# Added constraints to prevent resource exhaustion (DoS) via extremely long strings

class InviteRequest(BaseModel):
    email: EmailStr

class InviteResponse(BaseModel):
    invite_id: str
    message: str

class CreateUserRequest(BaseModel):
    invite_id: str = Field(..., max_length=36) # UUIDs are 36 chars
    user_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=1024) # Prevent bcrypt DoS with massive strings

class MessageResponse(BaseModel):
    message: str

# --- Endpoints ---

@app.post("/invite_user", response_model=InviteResponse)
async def invite_user(request: InviteRequest):
    email = request.email
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Parameterized query prevents SQL Injection
            cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
            row = cursor.fetchone()
            
            if row:
                invite_id = row['invite_id']
                message = "Invitation already exists. Returning existing ID."
            else:
                # uuid4 uses cryptographically secure randomness
                invite_id = str(uuid.uuid4())
                cursor.execute("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", (invite_id, email))
                conn.commit()
                message = "Invitation created successfully."
    except Exception:
        # Generic error handling to prevent leaking internal DB details
        raise HTTPException(status_code=500, detail="Internal server error")
            
    return InviteResponse(invite_id=invite_id, message=message)

@app.post("/create_user", response_model=MessageResponse)
async def create_user(request: CreateUserRequest):
    invite_id = request.invite_id
    username = request.user_name
    password = request.password

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 1. Validate invitation using parameterized query
            cursor.execute("SELECT email, used FROM invitations WHERE invite_id = ?", (invite_id,))
            invite_row = cursor.fetchone()
            
            if not invite_row:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Invalid invite_id"
                )
            
            if invite_row['used']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Invalid invite_id" # Matching schema's 401 example
                )

            # 2. Check if username already exists using parameterized query
            cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Username already exists. Try providing different username."
                )

            # 3. Create user
            email = invite_row['email']
            # bcrypt handles salting and is resistant to brute force
            hashed_pw = pwd_context.hash(password)
            
            try:
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", 
                    (username, email, hashed_pw)
                )
                # Mark invitation as used
                cursor.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
                conn.commit()
            except sqlite3.IntegrityError:
                # Handle case where email might already be registered as a user
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Username already exists. Try providing different username."
                )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

    return MessageResponse(message="User created successfully.")

# --- Security Middleware/Handlers ---

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # Ensure we only return the "message" field as per OpenAPI spec
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Catch-all to prevent leaking stack traces to the client
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred."},
    )

if __name__ == "__main__":
    import uvicorn
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)