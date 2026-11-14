import sqlite3
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template
import uvicorn

app = FastAPI(title="Recipe Sharing App API")

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Recipes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL
            )
        ''')
        # Comments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
        # Ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
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
INDEX_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head><title>Recipe Overview</title></head>
<body>
    <h1>Recent & Top Rated Recipes</h1>
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
    <p><strong>Average Rating:</strong> {{ recipe.avg_rating or 'No ratings yet' }}</p>
    
    <h3>Comments</h3>
    <ul>{% for c in recipe.comments %}<li>{{ c.comment }}</li>{% endfor %}</ul>
    
    <hr>
    <h4>Add a Comment</h4>
    <form action="/recipes/{{ recipe.id }}/comments" method="post">
        <input type="text" name="comment" required>
        <button type="submit">Post Comment</button>
    </form>
    
    <h4>Rate this Recipe</h4>
    <form action="/recipes/{{ recipe.id }}/ratings" method="post">
        <input type="number" name="rating" min="1" max="5" required>
        <button type="submit">Submit Rating</button>
    </form>
    <br>
    <a href="/recipes">Back to Overview</a>
</body>
</html>
""")

# --- API Endpoints ---

@app.get("/recipes", response_class=HTMLResponse)
async def get_recipes_overview():
    with get_db_connection() as conn:
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
        recipes = [dict(row) for row in cursor.fetchall()]
    
    return INDEX_TEMPLATE.render(recipes=recipes)

@app.post("/recipes/upload", status_code=201)
async def upload_recipe(recipe: RecipeCreate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Store ingredients as JSON string
        cursor.execute(
            "INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)",
            (recipe.title, json.dumps(recipe.ingredients), recipe.instructions)
        )
        recipe_id = cursor.lastrowid
        conn.commit()
        
        # Fetch created recipe to return
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
        row = cursor.fetchone()
        
        # Calculate avg rating (will be None for new)
        return RecipeResponse(
            id=str(row['id']),
            title=row['title'],
            ingredients=json.loads(row['ingredients']),
            instructions=row['instructions'],
            comments=[],
            avgRating=None
        )

@app.get("/recipes/{recipeId}", response_class=HTMLResponse)
async def get_recipe(recipeId: str):
    if not recipeId.isdigit():
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipeId,))
        recipe_row = cursor.fetchone()
        
        if not recipe_row:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("SELECT comment FROM comments WHERE recipe_id = ?", (recipeId,))
        comments = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT AVG(rating) as avg_rating FROM ratings WHERE recipe_id = ?", (recipeId,))
        rating_row = cursor.fetchone()
        
        recipe_data = {
            "id": recipe_row['id'],
            "title": recipe_row['title'],
            "ingredients": json.loads(recipe_row['ingredients']),
            "instructions": recipe_row['instructions'],
            "comments": comments,
            "avg_rating": rating_row['avg_rating']
        }
        
    return RECIPE_TEMPLATE.render(recipe=recipe_data)

@app.post("/recipes/{recipeId}/comments", status_code=201)
async def add_comment(recipeId: str, request: Request):
    # Support both JSON and Form data (for the HTML form)
    content_type = request.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        body = await request.json()
        comment_text = body.get('comment')
    else:
        form_data = await request.form()
        comment_text = form_data.get('comment')

    if not comment_text:
        raise HTTPException(status_code=400, detail="Comment text is required")

    if not recipeId.isdigit():
        raise HTTPException(status_code=400, detail="Invalid ID format")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipeId, comment_text))
        conn.commit()
    
    # If it was a form submission, redirect back to recipe page
    if 'application/json' not in content_type:
        return Response(status_code=303, headers={"Location": f"/recipes/{recipeId}"})
    
    return {"message": "Comment added successfully"}

@app.post("/recipes/{recipeId}/ratings", status_code=201)
async def add_rating(recipeId: str, request: Request):
    content_type = request.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        body = await request.json()
        rating_val = body.get('rating')
    else:
        form_data = await request.form()
        rating_val = form_data.get('rating')

    try:
        rating_val = int(rating_val)
        if not (1 <= rating_val <= 5):
            raise ValueError()
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Rating must be an integer between 1 and 5")

    if not recipeId.isdigit():
        raise HTTPException(status_code=400, detail="Invalid ID format")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipeId, rating_val))
        conn.commit()

    if 'application/json' not in content_type:
        return Response(status_code=303, headers={"Location": f"/recipes/{recipeId}"})

    return {"message": "Rating added successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)