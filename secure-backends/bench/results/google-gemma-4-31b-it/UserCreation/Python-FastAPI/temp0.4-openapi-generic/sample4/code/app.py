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
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_change_me")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="InviteAPI")

# --- Database Setup ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Invitations table: stores email and unique invite_id
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                email TEXT PRIMARY KEY,
                invite_id TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)
        # Users table: stores username, hashed password and email
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
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

# --- API Endpoints ---

@app.post("/invite_user", response_model=InviteResponse)
async def invite_user(request: InviteRequest):
    """
    Create an invitation by the current user to create a new user.
    """
    email = request.email
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Check if invitation already exists for this email
        cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if row:
            invite_id = row['invite_id']
        else:
            # Generate a secure unique invite ID
            invite_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO invitations (email, invite_id) VALUES (?, ?)", (email, invite_id))
            conn.commit()
            
        return InviteResponse(
            invite_id=invite_id,
            message=f"Invitation successfully created for {email}"
        )

@app.post("/create_user", responses={200: {"model": MessageResponse}, 400: {"model": MessageResponse}, 401: {"model": MessageResponse}})
async def create_user(request: CreateUserRequest):
    """
    Given an invitation, create a user.
    """
    invite_id = request.invite_id
    username = request.user_name
    password = request.password

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Validate Invitation
        cursor.execute("SELECT email FROM invitations WHERE invite_id = ? AND used = 0", (invite_id,))
        invite_row = cursor.fetchone()
        
        if not invite_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail={"message": "Invalid invite_id"}
            )
        
        email = invite_row['email']

        # 2. Check if username already exists
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail={"message": "Username already exists. Try providing different username."}
            )

        # 3. Hash password and create user
        hashed_password = pwd_context.hash(password)
        try:
            cursor.execute(
                "INSERT INTO users (username, password, email) VALUES (?, ?, ?)", 
                (username, hashed_password, email)
            )
            # Mark invitation as used
            cursor.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            # Handle case where email might already be associated with a user
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail={"message": "User with this email already exists."}
            )

        return {"message": "User created successfully"}

# Override default exception handler to match the schema's response format (JSON object with 'message' key)
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    # If detail is already a dict with 'message', use it, otherwise wrap it
    detail = exc.detail
    if isinstance(detail, dict) and "message" in detail:
        content = detail
    else:
        content = {"message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)