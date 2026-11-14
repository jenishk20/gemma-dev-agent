import os
import sqlite3
import uuid
import hashlib
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

# Configuration
DATABASE_NAME = "db.sqlite3"
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev_only")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="InviteAPI")

# --- Database Logic ---

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Invitations table: stores the invite_id and associated email
        # used = 0 (pending), 1 (used)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                invite_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                email TEXT NOT NULL
            )
        """)
        conn.commit()

# Initialize DB on startup
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
    """
    Create an invitation by the current user to create a new user.
    """
    email = request.email
    
    with get_db_connection() as conn:
        # Check if an invitation already exists for this email
        cursor = conn.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if row:
            invite_id = row['invite_id']
            message = "Invitation already exists for this email."
        else:
            # Create a new unique invite ID
            invite_id = str(uuid.uuid4())
            conn.execute("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", (invite_id, email))
            conn.commit()
            message = "A new invitation has been created."
            
    return InviteResponse(invite_id=invite_id, message=message)

@app.post("/create_user", response_model=MessageResponse)
async def create_user(request: CreateUserRequest):
    """
    Given an invitation, create a user.
    """
    invite_id = request.invite_id
    username = request.user_name
    password = request.password

    with get_db_connection() as conn:
        # 1. Validate Invitation
        cursor = conn.execute("SELECT email, used FROM invitations WHERE invite_id = ?", (invite_id,))
        invite = cursor.fetchone()
        
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid invite_id"
            )
        
        if invite['used'] == 1:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="This invitation has already been used."
            )

        # 2. Check if username exists
        cursor = conn.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Username already exists. Try providing different username."
            )

        # 3. Create User and Mark Invite as used
        hashed_pw = pwd_context.hash(password)
        email = invite['email']
        
        try:
            conn.execute("INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)", 
                        (username, hashed_pw, email))
            conn.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    return MessageResponse(message="User created successfully")

# Override default FastAPI exception handler to match the schema's response format { "message": "..." }
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)