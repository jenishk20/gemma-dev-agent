import sqlite3
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template

app = FastAPI()

DB_PATH = "db.sqlite3"

# --- Database Setup ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        # Recipes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL
            )
        ''')
        # Comments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id TEXT NOT NULL,
                comment TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id)
            )
        ''')
        # Ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id)
            )
        ''')
        conn.commit()

init_db()

# --- Models ---
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
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Recipe Sharing App</title></head>
<body>
    <h1>Recent & Top Rated Recipes</h1>
    <ul>
        {% for recipe in recipes %}
        <li><a href="/recipes/{{ recipe.id }}">{{ recipe.title }}</a></li>
        {% endfor %}
    </ul>
</body>
</html>
"""

RECIPE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>{{ recipe.title }}</title></head>
<body>
    <h1>{{ recipe.title }}</h1>
    <p><strong>Average Rating:</strong> {{ recipe.avgRating if recipe.avgRating else 'No ratings yet' }}</p>
    <h3>Ingredients</h3>
    <ul>
        {% for ing in recipe.ingredients %}<li>{{ ing }}</li>{% endfor %}
    </ul>
    <h3>Instructions</h3>
    <p>{{ recipe.instructions }}</p>
    <h3>Comments</h3>
    <ul>
        {% for c in recipe.comments %}<li>{{ c.comment }}</li>{% endfor %}
    </ul>
    <hr>
    <a href="/recipes">Back to Overview</a>
</body>
</html>
"""

# --- Endpoints ---

@app.get("/recipes", response_class=HTMLResponse)
async def get_recipes_overview():
    with get_db() as conn:
        cursor = conn.cursor()
        # Simple logic: Get recipes ordered by avg rating descending
        query = '''
            SELECT r.id, r.title, AVG(rt.rating) as avg_rating 
            FROM recipes r 
            LEFT JOIN ratings rt ON r.id = rt.recipe_id 
            GROUP BY r.id 
            ORDER BY avg_rating DESC, r.id DESC
        '''
        cursor.execute(query)
        rows = cursor.fetchall()
        recipes = [{"id": row["id"], "title": row["title"]} for row in rows]
    
    return Template(INDEX_TEMPLATE).render(recipes=recipes)

@app.post("/recipes/upload", status_code=201)
async def upload_recipe(recipe: RecipeCreate):
    recipe_id = str(uuid.uuid4())
    ingredients_str = ",".join(recipe.ingredients) # Simple serialization
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)",
            (recipe_id, recipe.title, ingredients_str, recipe.instructions)
        )
        conn.commit()
    
    return {
        "id": recipe_id,
        "title": recipe.title,
        "ingredients": recipe.ingredients,
        "instructions": recipe.instructions,
        "comments": [],
        "avgRating": None
    }

@app.get("/recipes/{recipeId}", response_class=HTMLResponse)
async def get_recipe(recipeId: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipeId,))
        recipe_row = cursor.fetchone()
        
        if not recipe_row:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("SELECT comment FROM comments WHERE recipe_id = ?", (recipeId,))
        comments = [{"comment": row["comment"]} for row in cursor.fetchall()]
        
        cursor.execute("SELECT AVG(rating) as avg FROM ratings WHERE recipe_id = ?", (recipeId,))
        avg_row = cursor.fetchone()
        avg_rating = avg_row["avg"] if avg_row else None

        recipe_data = {
            "id": recipe_row["id"],
            "title": recipe_row["title"],
            "ingredients": recipe_row["ingredients"].split(","),
            "instructions": recipe_row["instructions"],
            "comments": comments,
            "avgRating": avg_rating
        }
        
    return Template(RECIPE_TEMPLATE).render(recipe=recipe_data)

@app.post("/recipes/{recipeId}/comments", status_code=201)
async def add_comment(recipeId: str, comment_data: CommentCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", 
                      (recipeId, comment_data.comment))
        conn.commit()
    return {"message": "Comment added successfully"}

@app.post("/recipes/{recipeId}/ratings", status_code=201)
async def add_rating(recipeId: str, rating_data: RatingCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", 
                      (recipeId, rating_data.rating))
        conn.commit()
    return {"message": "Rating added successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)