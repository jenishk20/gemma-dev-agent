import sqlite3
import json
import html
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Recipe Sharing App API")

DB_FILE = "db.sqlite3"

# --- Database Setup ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
        conn.commit()

init_db()

# --- Pydantic Models ---
class RecipeCreate(BaseModel):
    title: str = Field(..., max_length=1000)
    ingredients: List[str] = Field(..., max_length=100) # Bound list size
    instructions: str = Field(..., max_length=10000)

class CommentCreate(BaseModel):
    comment: str = Field(..., max_length=2000)

class RatingCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)

class CommentSchema(BaseModel):
    comment: str

class RecipeSchema(BaseModel):
    id: str
    title: str
    ingredients: List[str]
    instructions: str
    comments: List[CommentSchema]
    avgRating: Optional[float]

# --- Helper Functions ---
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def validate_id(recipe_id: str):
    """Ensure recipeId is a numeric string to prevent unexpected SQL behavior 
    and ensure it's treated as an integer by the DB."""
    if not recipe_id.isdigit():
        raise HTTPException(status_code=400, detail="Invalid recipe ID format")
    return int(recipe_id)

# --- Routes ---

@app.get("/recipes", response_class=HTMLResponse)
async def get_recipes_overview():
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Parameterized query (though no user input here)
        query = '''
            SELECT r.id, r.title, AVG(ra.rating) as avg_rating 
            FROM recipes r 
            LEFT JOIN ratings ra ON r.id = ra.recipe_id 
            GROUP BY r.id 
            ORDER BY avg_rating DESC, r.id DESC
        '''
        cursor.execute(query)
        recipes = cursor.fetchall()
        conn.close()

        # Escape HTML output to prevent XSS
        html_content = "<h1>Recipe Overview</h1><ul>"
        for row in recipes:
            title_esc = html.escape(row["title"])
            id_val = row["id"]
            rating_val = html.escape(str(row["avg_rating"])) if row["avg_rating"] is not None else "N/A"
            html_content += f'<li><a href="/recipes/{id_val}">{title_esc}</a> (Rating: {rating_val})</li>'
        html_content += "</ul>"
        return HTMLResponse(content=html_content)
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/recipes/upload", status_code=201, response_model=RecipeSchema)
async def upload_recipe(recipe: RecipeCreate):
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Use parameterized queries to prevent SQL Injection
        ingredients_json = json.dumps(recipe.ingredients)
        cursor.execute(
            "INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)",
            (recipe.title, ingredients_json, recipe.instructions)
        )
        recipe_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return RecipeSchema(
            id=str(recipe_id),
            title=recipe.title,
            ingredients=recipe.ingredients,
            instructions=recipe.instructions,
            comments=[],
            avgRating=None
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

@app.get("/recipes/{recipeId}", response_class=HTMLResponse)
async def get_recipe(recipeId: str):
    # Validate and sanitize ID
    rid = validate_id(recipeId)
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (rid,))
        recipe_row = cursor.fetchone()
        if not recipe_row:
            conn.close()
            raise HTTPException(status_code=404, detail="Recipe not found")

        cursor.execute("SELECT comment FROM comments WHERE recipe_id = ?", (rid,))
        comments = cursor.fetchall()
        
        cursor.execute("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", (rid,))
        avg_rating_row = cursor.fetchone()
        avg_rating = avg_rating_row[0] if avg_rating_row else None
        conn.close()

        # Escape all user-generated content to prevent XSS
        title_esc = html.escape(recipe_row["title"])
        instructions_esc = html.escape(recipe_row["instructions"])
        
        ingredients = json.loads(recipe_row["ingredients"])
        ing_list = "".join([f"<li>{html.escape(i)}</li>" for i in ingredients])
        com_list = "".join([f"<li>{html.escape(c['comment'])}</li>" for c in comments])
        
        rating_display = html.escape(str(avg_rating)) if avg_rating is not None else 'No ratings yet'

        html_content = f"""
        <h1>{title_esc}</h1>
        <p><strong>Average Rating:</strong> {rating_display}</p>
        <h3>Ingredients</h3>
        <ul>{ing_list}</ul>
        <h3>Instructions</h3>
        <p>{instructions_esc}</p>
        <h3>Comments</h3>
        <ul>{com_list}</ul>
        <hr>
        <form action="/recipes/{recipeId}/comments" method="post">
            <input type="text" name="comment" placeholder="Add a comment" required>
            <button type="submit">Post Comment</button>
        </form>
        <form action="/recipes/{recipeId}/ratings" method="post">
            <input type="number" name="rating" min="1" max="5" placeholder="Rating (1-5)" required>
            <button type="submit">Rate</button>
        </form>
        <br><a href="/recipes">Back to Overview</a>
        """
        return HTMLResponse(content=html_content)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/recipes/{recipeId}/comments", status_code=201)
async def add_comment(recipeId: str, payload: CommentCreate):
    rid = validate_id(recipeId)
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (rid,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (rid, payload.comment))
        conn.commit()
        conn.close()
        return {"message": "Comment added successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

@app.post("/recipes/{recipeId}/ratings", status_code=201)
async def add_rating(recipeId: str, payload: RatingCreate):
    rid = validate_id(recipeId)
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (rid,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (rid, payload.rating))
        conn.commit()
        conn.close()
        return {"message": "Rating added successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)