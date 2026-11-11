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
# APP_SECRET is provided via env, though not explicitly used for JWTs in this specific schema
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")

# Password hashing setup: bcrypt is a strong salted KDF
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="InviteAPI")

# --- Database Setup ---

def get_db():
    # Use check_same_thread=False for FastAPI's async environment
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Table for invitations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                invite_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)
        # Table for users
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        conn.commit()

init_db()

# --- Pydantic Models ---
# Added constraints to prevent resource exhaustion (DoS) via massive strings

class InviteRequest(BaseModel):
    email: EmailStr

class InviteResponse(BaseModel):
    invite_id: str
    message: str

class CreateUserRequest(BaseModel):
    invite_id: str = Field(..., max_length=36) # UUIDs are 36 chars
    user_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)

class MessageResponse(BaseModel):
    message: str

# --- Endpoints ---

@app.post("/invite_user", response_model=InviteResponse)
async def invite_user(request: InviteRequest):
    """
    Create an invitation by the current user to create a new user.
    """
    email = request.email
    
    with get_db() as conn:
        cursor = conn.cursor()
        # Parameterized query prevents SQL Injection
        cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if row:
            invite_id = row["invite_id"]
            message = "Invitation already exists. Returning existing ID."
        else:
            # uuid4 provides cryptographically secure randomness
            invite_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", (invite_id, email))
            conn.commit()
            message = "Invitation created successfully."
            
        return InviteResponse(invite_id=invite_id, message=message)

@app.post("/create_user", responses={200: {"model": MessageResponse}, 400: {"model": MessageResponse}, 401: {"model": MessageResponse}})
async def create_user(request: CreateUserRequest):
    """
    Given an invitation, create a user.
    """
    invite_id = request.invite_id
    user_name = request.user_name
    password = request.password

    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Validate Invitation (Parameterized query)
        cursor.execute("SELECT email FROM invitations WHERE invite_id = ? AND used = 0", (invite_id,))
        invite_row = cursor.fetchone()
        
        if not invite_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid invite_id"
            )
        
        email = invite_row["email"]

        # 2. Check if username already exists (Parameterized query)
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (user_name,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Username already exists. Try providing different username."
            )

        # 3. Create User
        # bcrypt handles salting and is resistant to brute force
        hashed_password = pwd_context.hash(password)
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", 
                (user_name, email, hashed_password)
            )
            # Mark invitation as used
            cursor.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            # Handle case where email is already associated with another user
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="This email is already registered to an account."
            )

        return MessageResponse(message="User created")

# --- Security & Error Handling ---

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # Ensures we return the exact JSON format required by the schema and don't leak internals
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Catch-all to prevent leaking stack traces (Internal Server Error)
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred."},
    )

if __name__ == "__main__":
    import uvicorn
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)