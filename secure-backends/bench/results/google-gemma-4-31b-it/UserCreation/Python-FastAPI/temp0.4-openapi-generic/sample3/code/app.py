import os
import sqlite3
import uuid
import hashlib
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import uvicorn

# Configuration
DB_PATH = "db.sqlite3"
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_change_me")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="InviteAPI", version="1.0.11")

# --- Database Setup ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        # Invitations table: stores email and a unique invite_id
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                email TEXT PRIMARY KEY,
                invite_id TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)
        # Users table: stores user details
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
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
            message = "Invitation already exists for this email."
        else:
            # Create a new unique invitation ID
            invite_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO invitations (email, invite_id) VALUES (?, ?)", (email, invite_id))
            conn.commit()
            message = "Invitation created successfully."
            
    return InviteResponse(invite_id=invite_id, message=message)

@app.post("/create_user", responses={200: {"model": MessageResponse}, 400: {"model": MessageResponse}, 401: {"model": MessageResponse}})
async def create_user(request: CreateUserRequest):
    """
    Given an invitation, create a user.
    """
    invite_id = request.invite_id
    username = request.user_name
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
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Username already exists. Try providing different username."
            )
        
        # 3. Hash password and save user
        hashed_pw = pwd_context.hash(password)
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, user_email, hashed_pw)
            )
            # Mark invitation as used
            cursor.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Username or Email already registered."
            )

    return {"message": "User created successfully"}

# Override the default FastAPI exception handler to match the required JSON response format { "message": "..." }
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastApiHTTPException

@app.exception_handler(FastApiHTTPException)
async def custom_http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)