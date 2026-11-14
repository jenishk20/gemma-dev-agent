import sqlite3
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template, escape

app = FastAPI(title="Recipe Sharing App API")

DB_FILE = "db.sqlite3"

# --- Database Setup ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id TEXT NOT NULL,
                comment TEXT NOT NULL,
                FOREIGN KEY(recipe_id) REFERENCES recipes(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                FOREIGN KEY(recipe_id) REFERENCES recipes(id)
            )
        ''')
        conn.commit()

init_db()

# --- Models ---
class RecipeCreate(BaseModel):
    title: str = Field(..., max_length=1000)
    ingredients: List[str] = Field(..., max_items=100)
    instructions: str = Field(..., max_length=10000)

class RecipeResponse(BaseModel):
    id: str
    title: str
    ingredients: List[str]
    instructions: str
    comments: List[dict]
    avgRating: Optional[float]

class CommentCreate(BaseModel):
    comment: str = Field(..., max_length=2000)

class RatingCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)

# --- HTML Templates ---
# Note: Jinja2 auto-escapes by default when using render() if configured, 
# but we use the Template object here. We will manually escape variables 
# to ensure no XSS occurs when rendering.
INDEX_TEMPLATE = """
<html lang="en">
    <head><title>Recipe Overview</title></head>
    <body>
        <h1>Recent and Top Rated Recipes</h1>
        <ul>
            {% for recipe in recipes %}
            <li><a href="/recipes/{{ recipe.id }}">{{ recipe.title }}</a></li>
            {% endfor %}
        </ul>
    </body>
</html>
"""

RECIPE_TEMPLATE = """
<html lang="en">
    <head><title>{{ recipe.title }}</title></head>
    <body>
        <h1>{{ recipe.title }}</h1>
        <p><strong>Average Rating:</strong> {{ recipe.avgRating if recipe.avgRating else 'No ratings yet' }}</p>
        <h3>Ingredients</h3>
        <ul>{% for ing in recipe.ingredients %}<li>{{ ing }}</li>{% endfor %}</ul>
        <h3>Instructions</h3>
        <p>{{ recipe.instructions }}</p>
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
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM recipes")
            rows = cursor.fetchall()
        
        # Escape data to prevent XSS
        recipes = [{"id": escape(r[0]), "title": escape(r[1])} for r in rows]
        return Template(INDEX_TEMPLATE).render(recipes=recipes)
    except Exception:
        raise HTTPException(status_code=500, detail="Server error")

@app.post("/recipes/upload", status_code=201, response_model=RecipeResponse)
async def upload_recipe(recipe: RecipeCreate):
    recipe_id = str(uuid.uuid4())
    # Use a delimiter that is unlikely to be in ingredients or handle as JSON
    # For simplicity and to match previous logic, we use a comma but ensure 
    # we don't trust the input blindly.
    ingredients_str = ",".join(recipe.ingredients)
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)",
                (recipe_id, recipe.title, ingredients_str, recipe.instructions)
            )
            conn.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")
    
    return RecipeResponse(
        id=recipe_id,
        title=recipe.title,
        ingredients=recipe.ingredients,
        instructions=recipe.instructions,
        comments=[],
        avgRating=None
    )

@app.get("/recipes/{recipeId}", response_class=HTMLResponse)
async def get_recipe(recipeId: str):
    # Basic validation for recipeId to prevent unexpected characters
    if not recipeId.isalnum() and '-' not in recipeId:
        raise HTTPException(status_code=404, detail="Recipe not found")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT title, ingredients, instructions FROM recipes WHERE id = ?", (recipeId,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Recipe not found")
            
            title, ingredients_str, instructions = row
            
            cursor.execute("SELECT comment FROM comments WHERE recipe_id = ?", (recipeId,))
            comments = [{"comment": escape(r[0])} for r in cursor.fetchall()]
            
            cursor.execute("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", (recipeId,))
            avg_rating = cursor.fetchone()[0]

        recipe_data = {
            "id": escape(recipeId),
            "title": escape(title),
            "ingredients": [escape(ing) for ing in (ingredients_str.split(",") if ingredients_str else [])],
            "instructions": escape(instructions),
            "comments": comments,
            "avgRating": avg_rating
        }
        return Template(RECIPE_TEMPLATE).render(recipe=recipe_data)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Server error")

@app.post("/recipes/{recipeId}/comments", status_code=201)
async def add_comment(recipeId: str, comment_data: CommentCreate):
    if not recipeId.isalnum() and '-' not in recipeId:
        raise HTTPException(status_code=404, detail="Recipe not found")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Recipe not found")
            
            cursor.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipeId, comment_data.comment))
            conn.commit()
        return {"message": "Comment added successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

@app.post("/recipes/{recipeId}/ratings", status_code=201)
async def add_rating(recipeId: str, rating_data: RatingCreate):
    if not recipeId.isalnum() and '-' not in recipeId:
        raise HTTPException(status_code=404, detail="Recipe not found")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Recipe not found")
            
            cursor.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipeId, rating_data.rating))
            conn.commit()
        return {"message": "Rating added successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)