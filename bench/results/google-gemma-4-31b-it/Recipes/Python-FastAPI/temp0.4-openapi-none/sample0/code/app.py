import sqlite3
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template
import uvicorn

app = FastAPI()
DB_FILE = "db.sqlite3"

# --- Database Setup ---
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        """)
        conn.commit()

init_db()

# --- Pydantic Models ---
class RecipeCreate(BaseModel):
    title: str
    ingredients: List[str]
    instructions: str

class RecipeResponse(BaseModel):
    id: str
    title: str
    ingredients: List[str]
    instructions: str
    comments: List[dict]
    avgRating: Optional[float]

class CommentCreate(BaseModel):
    comment: str

class RatingCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)

# --- HTML Templates ---
OVERVIEW_TEMPLATE = """
<html>
<head><title>Recipe Sharing App</title></head>
<body>
    <h1>Recent and Top-Rated Recipes</h1>
    <ul>
        {% for recipe in recipes %}
        <li><a href="/recipes/{{ recipe.id }}">{{ recipe.title }}</a> (Rating: {{ recipe.avg_rating or 'N/A' }})</li>
        {% endfor %}
    </ul>
</body>
</html>
"""

DETAIL_TEMPLATE = """
<html>
<head><title>{{ recipe.title }}</title></head>
<body>
    <h1>{{ recipe.title }}</h1>
    <p><strong>Ingredients:</strong></p>
    <ul>{% for ing in recipe.ingredients %}<li>{{ ing }}</li>{% endfor %}</ul>
    <p><strong>Instructions:</strong> {{ recipe.instructions }}</p>
    <p><strong>Average Rating:</strong> {{ recipe.avg_rating or 'No ratings yet' }}</p>
    
    <h3>Comments</h3>
    <ul>{% for c in recipe.comments %}<li>{{ c.comment }}</li>{% endfor %}</ul>
    
    <hr>
    <a href="/recipes">Back to Overview</a>
</body>
</html>
"""

# --- API Endpoints ---

@app.get("/recipes", response_class=HTMLResponse)
async def get_recipes_overview():
    with get_db() as conn:
        cursor = conn.cursor()
        # Get recipes and their average ratings
        query = """
            SELECT r.id, r.title, AVG(ra.rating) as avg_rating 
            FROM recipes r 
            LEFT JOIN ratings ra ON r.id = ra.recipe_id 
            GROUP BY r.id 
            ORDER BY avg_rating DESC, r.id DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        recipes = [{"id": row["id"], "title": row["title"], "avg_rating": row["avg_rating"]} for row in rows]
    
    return Template(OVERVIEW_TEMPLATE).render(recipes=recipes)

@app.post("/recipes/upload", status_code=201)
async def upload_recipe(recipe: RecipeCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)",
            (recipe.title, json.dumps(recipe.ingredients), recipe.instructions)
        )
        recipe_id = cursor.lastrowid
        conn.commit()
        
        # Return the created recipe object as per schema
        return {
            "id": str(recipe_id),
            "title": recipe.title,
            "ingredients": recipe.ingredients,
            "instructions": recipe.instructions,
            "comments": [],
            "avgRating": None
        }

@app.get("/recipes/{recipeId}", response_class=HTMLResponse)
async def get_recipe(recipeId: str):
    try:
        rid = int(recipeId)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid ID format")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (rid,))
        recipe_row = cursor.fetchone()
        if not recipe_row:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("SELECT comment FROM comments WHERE recipe_id = ?", (rid,))
        comments = [{"comment": row["comment"]} for row in cursor.fetchall()]
        
        cursor.execute("SELECT AVG(rating) as avg_rating FROM ratings WHERE recipe_id = ?", (rid,))
        rating_row = cursor.fetchone()
        
        recipe_data = {
            "id": recipe_row["id"],
            "title": recipe_row["title"],
            "ingredients": json.loads(recipe_row["ingredients"]),
            "instructions": recipe_row["instructions"],
            "comments": comments,
            "avg_rating": rating_row["avg_rating"]
        }
        
    return Template(DETAIL_TEMPLATE).render(recipe=recipe_data)

@app.post("/recipes/{recipeId}/comments", status_code=201)
async def add_comment(recipeId: str, comment_data: CommentCreate):
    try:
        rid = int(recipeId)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid ID format")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (rid,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (rid, comment_data.comment))
        conn.commit()
    
    return {"message": "Comment added successfully"}

@app.post("/recipes/{recipeId}/ratings", status_code=201)
async def add_rating(recipeId: str, rating_data: RatingCreate):
    try:
        rid = int(recipeId)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid ID format")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (rid,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (rid, rating_data.rating))
        conn.commit()
        
    return {"message": "Rating added successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)