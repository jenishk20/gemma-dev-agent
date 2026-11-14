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
APP_SECRET = os.getenv("APP_SECRET", "default_secret_for_dev_only")

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
                user_name TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        conn.commit()

@app.on_event("startup")
def startup_event():
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

# --- Routes ---

@app.post("/invite_user", response_model=InviteResponse)
async def invite_user(request: InviteRequest):
    """
    Create an invitation by the current user to create a new user.
    """
    email = request.email
    
    with get_db() as conn:
        cursor = conn.cursor()
        # Check if an invitation already exists for this email
        cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if row:
            invite_id = row['invite_id']
            return InviteResponse(
                invite_id=invite_id, 
                message="Invitation already exists for this email."
            )
        
        # Create new invitation
        invite_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", (invite_id, email))
        conn.commit()
        
        return InviteResponse(
            invite_id=invite_id, 
            message="Invitation created successfully."
        )

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
        
        # 1. Validate Invitation
        cursor.execute("SELECT email FROM invitations WHERE invite_id = ? AND used = 0", (invite_id,))
        invite_row = cursor.fetchone()
        
        if not invite_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid invite_id"
            )
        
        user_email = invite_row['email']
        
        # 2. Check if username already exists
        cursor.execute("SELECT 1 FROM users WHERE user_name = ?", (user_name,))
        if cursor.fetchone():
            # The schema requires a 400 response with a specific message format
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Username already exists. Try providing different username."
            )
        
        # 3. Hash password and create user
        hashed_password = pwd_context.hash(password)
        try:
            cursor.execute(
                "INSERT INTO users (user_name, email, password_hash) VALUES (?, ?, ?)", 
                (user_name, user_email, hashed_password)
            )
            # Mark invitation as used
            cursor.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            # Handle race condition where username was taken between check and insert
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Username already exists. Try providing different username."
            )

    return MessageResponse(message="User created successfully")

# Custom exception handler to match the OpenAPI schema's response body {"message": "..."}
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastapiHTTPException

@app.exception_handler(FastapiHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)