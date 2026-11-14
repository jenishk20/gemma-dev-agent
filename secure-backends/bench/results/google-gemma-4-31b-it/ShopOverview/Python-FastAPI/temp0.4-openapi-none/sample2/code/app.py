import os
import sqlite3
import csv
import io
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Cookie
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from jose import jwt
from passlib.context import CryptContext
from jinja2 import Template

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")
ALGORITHM = "HS256"
DB_PATH = "db.sqlite3"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Merchant WebApp API")

# --- Database Setup ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS merchants (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_email TEXT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                FOREIGN KEY(merchant_email) REFERENCES merchants(email)
            )
        """)
        conn.commit()

init_db()

# --- Models ---
class MerchantRegister(BaseModel):
    email: EmailStr
    name: str
    password: str

class MerchantLogin(BaseModel):
    email: EmailStr
    password: str

class WareUpload(BaseModel):
    csv: str

# --- Auth Helpers ---
def create_access_token(data: dict):
    return jwt.encode(data, APP_SECRET, algorithm=ALGORITHM)

def get_current_merchant(auth_cookie: Optional[str] = Cookie(None, alias="AUTH_COOKIE")):
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(auth_cookie, APP_SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")

# --- Routes ---

@app.post("/merchants/register", status_code=201)
async def register(merchant: MerchantRegister):
    hashed_pw = pwd_context.hash(merchant.password)
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)",
                (merchant.email, merchant.name, hashed_pw)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Merchant already exists")
    return {"message": "Merchant registered successfully"}

@app.post("/merchants/login")
async def login(credentials: MerchantLogin):
    with get_db() as conn:
        user = conn.execute("SELECT * FROM merchants WHERE email = ?", (credentials.email,)).fetchone()
        if not user or not pwd_context.verify(credentials.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": credentials.email})
    response = Response(content="Login successful", media_type="application/json")
    response.set_cookie(key="AUTH_COOKIE", value=token, httponly=True)
    return response

@app.post("/merchants/upload-wares")
async def upload_wares(upload: WareUpload, merchant_email: str = Depends(get_current_merchant)):
    try:
        f = io.StringIO(upload.csv)
        reader = csv.DictReader(f)
        # Expected columns: name, description, price
        rows = []
        for row in reader:
            if not all(k in row for k in ("name", "description", "price")):
                raise ValueError("Missing columns")
            rows.append((merchant_email, row["name"], row["description"], float(row["price"])))
        
        with get_db() as conn:
            conn.executemany(
                "INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)",
                rows
            )
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
    
    return {"message": "Wares uploaded successfully"}

@app.get("/wares", response_class=HTMLResponse)
async def get_wares(
    minPrice: Optional[float] = None, 
    maxPrice: Optional[float] = None, 
    auth_cookie: Optional[str] = Cookie(None, alias="AUTH_COOKIE")
):
    # The schema says security: cookieAuth, implying it's required to view the page
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    query = "SELECT wares.name, wares.price, wares.description, merchants.email FROM wares JOIN merchants ON wares.merchant_email = merchants.email WHERE 1=1"
    params = []
    
    if minPrice is not None:
        query += " AND wares.price >= ?"
        params.append(minPrice)
    if maxPrice is not None:
        query += " AND wares.price <= ?"
        params.append(maxPrice)
        
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    
    # Render HTML Table
    template = Template("""
    <html>
    <head><title>Warehouse</title></head>
    <body>
        <h2>Offered Wares</h2>
        <table border="1">
            <tr>
                <th>Name</th>
                <th>Price</th>
                <th>Description</th>
                <th>Merchant Email</th>
            </tr>
            {% for row in rows %}
            <tr>
                <td>{{ row.name }}</td>
                <td>{{ row.price }}</td>
                <td>{{ row.description }}</td>
                <td>{{ row.email }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """)
    
    return template.render(rows=rows)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)