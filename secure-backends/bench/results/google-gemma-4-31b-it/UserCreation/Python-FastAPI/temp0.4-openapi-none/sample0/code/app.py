import os
import sqlite3
import uuid
import hashlib
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

# Configuration
DB_PATH = "db.sqlite3"
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="InviteAPI")

# --- Database Setup ---

def get_db():
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

class InviteRequest(BaseModel):
    email: EmailStr

class InviteResponse(BaseModel):
    invite_id: str
    message: str

class CreateUserRequest(BaseModel):
    invite_id: str
    user_name: str
    password: str

class MessageResponse(BaseModel):
    message: str

# --- Endpoints ---

@app.post("/invite_user", response_model=InviteResponse)
async def invite_user(request: InviteRequest):
    email = request.email
    
    with get_db() as conn:
        cursor = conn.cursor()
        # Check if an invitation already exists for this email
        cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if row:
            invite_id = row['invite_id']
            message = "Invitation already exists. Returning existing ID."
        else:
            # Create a new unique invitation ID
            invite_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", (invite_id, email))
            conn.commit()
            message = "Invitation created successfully."
            
    return InviteResponse(invite_id=invite_id, message=message)

@app.post("/create_user", response_model=MessageResponse)
async def create_user(request: CreateUserRequest):
    invite_id = request.invite_id
    username = request.user_name
    password = request.password

    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Validate invitation
        cursor.execute("SELECT email, used FROM invitations WHERE invite_id = ?", (invite_id,))
        invite_row = cursor.fetchone()
        
        if not invite_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid invite_id"
            )
        
        # Note: The schema doesn't explicitly forbid reusing an invite_id, 
        # but typically invitations are one-time use.
        # However, the schema says "Given an id... create a new user".
        # We'll check if it was already used to be safe.
        if invite_row['used']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invitation has already been used."
            )

        # 2. Check if username already exists
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Username already exists. Try providing different username."
            )

        # 3. Create user
        email = invite_row['email']
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
                detail="Email already associated with an account."
            )

    return MessageResponse(message="User created successfully.")

# Override the default exception handler to match the schema's response format { "message": "..." }
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import Request

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)