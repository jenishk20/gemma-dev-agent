import os
import sqlite3
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext

# Configuration
DB_FILE = "db.sqlite3"
# APP_SECRET is provided via env, though not explicitly used for JWTs in this specific API schema,
# it is kept for consistency with requirements.
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_change_me")

# Password hashing setup: bcrypt is a strong salted KDF
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="InviteAPI", version="1.0.11")

# --- Database Setup ---
def get_db_connection():
    # Using a context manager for connection ensures it closes.
    # sqlite3 is used with parameterized queries to prevent SQL Injection.
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                invite_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)
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
# Added constraints to prevent resource exhaustion (DoS) via massive strings
class InviteRequest(BaseModel):
    email: EmailStr

class InviteResponse(BaseModel):
    invite_id: str
    message: str

class CreateUserRequest(BaseModel):
    invite_id: str = Field(..., max_length=36)
    user_name: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)

class CreateUserResponse(BaseModel):
    message: str

# --- API Endpoints ---

@app.post("/invite_user", response_model=InviteResponse)
async def invite_user(request: InviteRequest):
    """
    Create an invitation by the current user to create a new user.
    """
    email = request.email
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Parameterized query prevents SQL Injection
            cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
            row = cursor.fetchone()
            
            if row:
                return InviteResponse(
                    invite_id=row['invite_id'], 
                    message="Invitation already exists. Returning existing ID."
                )
            
            # uuid4 provides cryptographically secure randomness for the invite_id
            invite_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", (invite_id, email))
            conn.commit()
            
            return InviteResponse(
                invite_id=invite_id, 
                message="Invitation created successfully."
            )
    except sqlite3.IntegrityError:
        # Handle race condition: if email was inserted between SELECT and INSERT
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
            row = cursor.fetchone()
            return InviteResponse(
                invite_id=row['invite_id'], 
                message="Invitation already exists. Returning existing ID."
            )
    except Exception:
        # Generic error handling to prevent leaking internal stack traces
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail={"message": "An internal server error occurred."}
        )

@app.post("/create_user", responses={200: {"model": CreateUserResponse}, 400: {"model": CreateUserResponse}, 401: {"model": CreateUserResponse}})
async def create_user(request: CreateUserRequest):
    """
    Given an invitation, create a user.
    """
    invite_id = request.invite_id
    user_name = request.user_name
    password = request.password
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Validate Invitation (Parameterized)
            cursor.execute("SELECT email FROM invitations WHERE invite_id = ? AND used = 0", (invite_id,))
            invite_row = cursor.fetchone()
            
            if not invite_row:
                # Return 401 as per OpenAPI spec
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail={"message": "Invalid invite_id"}
                )
            
            user_email = invite_row['email']
            
            # 2. Check if username already exists (Parameterized)
            cursor.execute("SELECT 1 FROM users WHERE username = ?", (user_name,))
            if cursor.fetchone():
                # Return 400 as per OpenAPI spec
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail={"message": "Username already exists. Try providing different username."}
                )
            
            # 3. Create User and mark invitation as used
            # pwd_context.hash uses bcrypt (strong salted KDF)
            hashed_pw = pwd_context.hash(password)
            
            cursor.execute("INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)", 
                           (user_name, hashed_pw, user_email))
            cursor.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
            conn.commit()
            
            return CreateUserResponse(message="User created successfully")
            
    except HTTPException:
        # Re-raise FastAPI HTTP exceptions so they aren't caught by the general Exception block
        raise
    except Exception:
        # Prevent leaking internal database errors or stack traces
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail={"message": "An internal server error occurred."}
        )

if __name__ == "__main__":
    import uvicorn
    # Binding to 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)