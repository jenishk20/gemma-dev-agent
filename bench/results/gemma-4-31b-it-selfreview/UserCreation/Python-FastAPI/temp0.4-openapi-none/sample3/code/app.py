import os
import sqlite3
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
import uvicorn
from fastapi.responses import JSONResponse

# Configuration
DB_PATH = "db.sqlite3"
# APP_SECRET is provided via env, though not explicitly used for JWTs in this specific API spec
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")

# Password hashing setup: bcrypt is a strong salted KDF
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="InviteAPI")

# --- Database Setup ---
def get_db():
    # Using a context manager for the connection ensures it closes
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
                user_name TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        conn.commit()

init_db()

# --- Pydantic Models ---
# Added constraints to prevent resource exhaustion (DoS via massive strings)
class InviteRequest(BaseModel):
    email: EmailStr = Field(..., max_length=254)

class InviteResponse(BaseModel):
    invite_id: str
    message: str

class CreateUserRequest(BaseModel):
    invite_id: str = Field(..., max_length=100)
    user_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)

class MessageResponse(BaseModel):
    message: str

# --- Endpoints ---

@app.post("/invite_user", response_model=InviteResponse)
async def invite_user(request: InviteRequest):
    """
    Create an invitation by the current user to create a new user.
    """
    email = request.email
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Parameterized query prevents SQL Injection
            cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
            row = cursor.fetchone()
            
            if row:
                invite_id = row['invite_id']
                return InviteResponse(
                    invite_id=invite_id, 
                    message="Invitation already exists and has been retrieved."
                )
            
            # uuid4 provides cryptographically secure randomness for the token
            invite_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", (invite_id, email))
            conn.commit()
            
            return InviteResponse(
                invite_id=invite_id, 
                message="Invitation created successfully."
            )
    except Exception as e:
        # Generic error handling to prevent leaking internal DB details
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/create_user", responses={200: {"model": MessageResponse}, 400: {"model": MessageResponse}, 401: {"model": MessageResponse}})
async def create_user(request: CreateUserRequest):
    """
    Given an invitation, create a user.
    """
    invite_id = request.invite_id
    user_name = request.user_name
    password = request.password

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 1. Validate invitation (Parameterized query)
            cursor.execute("SELECT email FROM invitations WHERE invite_id = ? AND used = 0", (invite_id,))
            invite_row = cursor.fetchone()
            
            if not invite_row:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Invalid invite_id"
                )
            
            email = invite_row['email']
            
            # 2. Check if username already exists (Parameterized query)
            cursor.execute("SELECT 1 FROM users WHERE user_name = ?", (user_name,))
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Username already exists. Try providing different username."
                )

            # 3. Hash password using bcrypt (Strong salted KDF)
            hashed_password = pwd_context.hash(password)
            try:
                cursor.execute(
                    "INSERT INTO users (user_name, email, password_hash) VALUES (?, ?, ?)", 
                    (user_name, email, hashed_password)
                )
                # Mark invitation as used to prevent reuse (Replay attack)
                cursor.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
                conn.commit()
            except sqlite3.IntegrityError:
                # Handle case where email might already be associated with a user
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="User with this email already exists."
                )

            return MessageResponse(message="User created successfully.")
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

# Custom exception handler to ensure we only return the documented "message" format 
# and never leak stack traces or internal details.
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Catch-all to prevent leaking internal server errors/stack traces
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )

if __name__ == "__main__":
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)