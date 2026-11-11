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

# --- Database Setup ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Invitations table: stores email and a unique invite_id
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                invite_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)
        # Users table: stores user credentials
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                email TEXT NOT NULL
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

class CreateUserResponse(BaseModel):
    message: str

# --- API Endpoints ---

@app.post("/invite_user", response_model=InviteResponse)
async def invite_user(request: InviteRequest):
    """
    Create an invitation by the current user to create a new user.
    """
    email = request.email
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if an invitation already exists for this email
    cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
    row = cursor.fetchone()
    
    if row:
        invite_id = row['invite_id']
        conn.close()
        return InviteResponse(
            invite_id=invite_id, 
            message="Invitation already exists. Returning existing ID."
        )
    
    # Create new invitation
    invite_id = str(uuid.uuid4())
    try:
        cursor.execute("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", (invite_id, email))
        conn.commit()
    except sqlite3.IntegrityError:
        # Handle race condition if email was inserted between SELECT and INSERT
        conn.rollback()
        cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
        row = cursor.fetchone()
        invite_id = row['invite_id']
    finally:
        conn.close()

    return InviteResponse(
        invite_id=invite_id, 
        message="Invitation created successfully."
    )

@app.post("/create_user", responses={200: {"model": CreateUserResponse}, 400: {"model": CreateUserResponse}, 401: {"model": CreateUserResponse}})
async def create_user(request: CreateUserRequest):
    """
    Given an invitation, create a user.
    """
    invite_id = request.invite_id
    user_name = request.user_name
    password = request.password
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Validate Invitation
    cursor.execute("SELECT email FROM invitations WHERE invite_id = ? AND used = 0", (invite_id,))
    invite_row = cursor.fetchone()
    
    if not invite_row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail={"message": "Invalid invite_id"}
        )
    
    user_email = invite_row['email']
    
    # 2. Check if username already exists
    cursor.execute("SELECT 1 FROM users WHERE username = ?", (user_name,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail={"message": "Username already exists. Try providing different username."}
        )
    
    # 3. Create User and mark invitation as used
    hashed_pw = pwd_context.hash(password)
    try:
        cursor.execute("INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)", 
                       (user_name, hashed_pw, user_email))
        cursor.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail={"message": "Database error occurred"})
    
    conn.close()
    return CreateUserResponse(message="User created successfully")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)