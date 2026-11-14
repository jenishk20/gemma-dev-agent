import sqlite3
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template

app = FastAPI(title="Recipe Sharing App API")

# Database setup
DB_PATH = "db.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id TEXT NOT NULL,
                comment TEXT NOT NULL,
                FOREIGN KEY(recipe_id) REFERENCES recipes(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                FOREIGN KEY(recipe_id) REFERENCES recipes(id)
            )
        """)
        conn.commit()

init_db()

# Pydantic Models
class RecipeCreate(BaseModel):
    title: str
    ingredients: List[str]
    instructions: str

class CommentCreate(BaseModel):
    comment: str

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

# HTML Templates
INDEX_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head><title>Recipe Overview</title></head>
<body>
    <h1>Recent and Top Rated Recipes</h1>
    <ul>
    {% for recipe in recipes %}
        <li><a href="/recipes/{{ recipe.id }}">{{ recipe.title }}</a> (Rating: {{ recipe.avg_rating or 'N/A' }})</li>
    {% endfor %}
    </ul>
</body>
</html>
""")

RECIPE_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head><title>{{ recipe.title }}</title></head>
<body>
    <h1>{{ recipe.title }}</h1>
    <h3>Ingredients</h3>
    <ul>{% for ing in recipe.ingredients %}<li>{{ ing }}</li>{% endfor %}</ul>
    <h3>Instructions</h3>
    <p>{{ recipe.instructions }}</p>
    <h3>Average Rating: {{ recipe.avg_rating or 'No ratings yet' }}</h3>
    <h3>Comments</h3>
    <ul>{% for com in recipe.comments %}<li>{{ com }}</li>{% endfor %}</ul>
    <hr>
    <a href="/recipes">Back to Overview</a>
</body>
</html>
""")

@app.get("/recipes", response_class=HTMLResponse)
async def get_recipes_overview():
    with get_db() as conn:
        # Get recipes with their average rating
        query = """
            SELECT r.id, r.title, AVG(rt.rating) as avg_rating 
            FROM recipes r 
            LEFT JOIN ratings rt ON r.id = rt.recipe_id 
            GROUP BY r.id 
            ORDER BY avg_rating DESC, r.id DESC
        """
        rows = conn.execute(query).fetchall()
        recipes = [{"id": row["id"], "title": row["title"], "avg_rating": row["avg_rating"]} for row in rows]
        return INDEX_TEMPLATE.render(recipes=recipes)

@app.post("/recipes/upload", status_code=201, response_model=RecipeSchema)
async def upload_recipe(recipe: RecipeCreate):
    recipe_id = str(uuid.uuid4())
    ingredients_str = ",".join(recipe.ingredients)
    
    with get_db() as conn:
        conn.execute(
            "INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)",
            (recipe_id, recipe.title, ingredients_str, recipe.instructions)
        )
        conn.commit()
    
    return RecipeSchema(
        id=recipe_id,
        title=recipe.title,
        ingredients=recipe.ingredients,
        instructions=recipe.instructions,
        comments=[],
        avgRating=None
    )

@app.get("/recipes/{recipeId}", response_class=HTMLResponse)
async def get_recipe(recipeId: str):
    with get_db() as conn:
        recipe_row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipeId,)).fetchone()
        if not recipe_row:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        comments = conn.execute("SELECT comment FROM comments WHERE recipe_id = ?", (recipeId,)).fetchall()
        rating_row = conn.execute("SELECT AVG(rating) as avg FROM ratings WHERE recipe_id = ?", (recipeId,)).fetchone()
        
        recipe_data = {
            "title": recipe_row["title"],
            "ingredients": recipe_row["ingredients"].split(","),
            "instructions": recipe_row["instructions"],
            "comments": [row["comment"] for row in comments],
            "avg_rating": rating_row["avg"]
        }
        return RECIPE_TEMPLATE.render(recipe=recipe_data)

@app.post("/recipes/{recipeId}/comments", status_code=201)
async def add_comment(recipeId: str, comment_data: CommentCreate):
    with get_db() as conn:
        recipe = conn.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,)).fetchone()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        conn.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipeId, comment_data.comment))
        conn.commit()
    return {"message": "Comment added successfully"}

@app.post("/recipes/{recipeId}/ratings", status_code=201)
async def add_rating(recipeId: str, rating_data: RatingCreate):
    with get_db() as conn:
        recipe = conn.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,)).fetchone()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        conn.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipeId, rating_data.rating))
        conn.commit()
    return {"message": "Rating added successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)