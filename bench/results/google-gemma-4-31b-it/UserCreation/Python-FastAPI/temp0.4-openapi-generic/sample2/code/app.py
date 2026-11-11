import os
import sqlite3
import uuid
import hashlib
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

# Configuration
DB_FILE = "db.sqlite3"
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_change_me")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="InviteAPI", version="1.0.11")

# --- Database Logic ---

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Invitations table: stores email and a unique invite_id
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                email TEXT PRIMARY KEY,
                invite_id TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)
        # Users table: stores username, hashed password, and email
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        """)
        conn.commit()

init_db()

# --- Schemas ---

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
        # Check if invitation already exists for this email
        cursor = conn.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if row:
            invite_id = row["invite_id"]
            message = "Invitation already exists. Returning existing ID."
        else:
            # Generate a secure random ID
            invite_id = str(uuid.uuid4())
            conn.execute("INSERT INTO invitations (email, invite_id) VALUES (?, ?)", (email, invite_id))
            conn.commit()
            message = "Invitation created successfully."
            
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
        # 1. Validate the invite_id and get the associated email
        cursor = conn.execute("SELECT email FROM invitations WHERE invite_id = ? AND used = 0", (invite_id,))
        invite_row = cursor.fetchone()
        
        if not invite_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid invite_id"
            )
        
        email = invite_row["email"]

        # 2. Check if username already exists
        cursor = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Username already exists. Try providing different username."
            )

        # 3. Hash password and save user
        hashed_pw = pwd_context.hash(password)
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)", 
                (username, hashed_pw, email)
            )
            # Mark invitation as used
            conn.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            # Handle case where email might already be registered as a user
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Email already associated with an account."
            )

    return MessageResponse(message="User created successfully")

# Custom exception handler to match the OpenAPI schema requirement for 400/401 response bodies
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    # Start server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)