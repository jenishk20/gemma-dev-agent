import sqlite3
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template, escape
import uvicorn

app = FastAPI(title="Recipe Sharing App API")

# Database setup
DB_PATH = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
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
                FOREIGN KEY (recipe_id) REFERENCES recipes(id)
            )
        ''')
        # Ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id)
            )
        ''')
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

class RecipeResponse(BaseModel):
    id: str
    title: str
    ingredients: List[str]
    instructions: str
    comments: List[CommentSchema]
    avgRating: Optional[float]

# HTML Templates
# Note: Jinja2's Template.render() does not auto-escape by default unless using Environment.
# We will use the 'escape' filter or function to prevent XSS.
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Recipe Overview</title></head>
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
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{{ recipe.title }}</title></head>
<body>
    <h1>{{ recipe.title }}</h1>
    <h3>Ingredients</h3>
    <ul>{% for ing in recipe.ingredients %}<li>{{ ing }}</li>{% endfor %}</ul>
    <h3>Instructions</h3>
    <p>{{ recipe.instructions }}</p>
    <h3>Average Rating: {{ recipe.avg_rating or 'No ratings yet' }}</h3>
    
    <h3>Comments</h3>
    <ul>{% for c in recipe.comments %}<li>{{ c }}</li>{% endfor %}</ul>
    
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
"""

@app.get("/recipes", response_class=HTMLResponse)
async def get_recipes_overview():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.id, r.title, AVG(rt.rating) as avg_rating 
                FROM recipes r 
                LEFT JOIN ratings rt ON r.id = rt.recipe_id 
                GROUP BY r.id 
                ORDER BY avg_rating DESC, r.id DESC
            ''')
            recipes = cursor.fetchall()
        
        # Manually escape data for the template to prevent XSS
        processed_recipes = []
        for row in recipes:
            processed_recipes.append({
                "id": escape(str(row['id'])) if row['id'] else "",
                "title": escape(row['title']),
                "avg_rating": row['avg_rating']
            })
            
        template = Template(INDEX_TEMPLATE)
        return template.render(recipes=processed_recipes)
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/recipes/upload", status_code=201, response_model=RecipeResponse)
async def upload_recipe(recipe: RecipeCreate):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)",
                (recipe.title, json.dumps(recipe.ingredients), recipe.instructions)
            )
            recipe_id = cursor.lastrowid
            conn.commit()
            
            return RecipeResponse(
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
    # Validate recipeId is numeric to prevent potential injection or unexpected behavior
    if not recipeId.isdigit():
        raise HTTPException(status_code=404, detail="Recipe not found")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipeId,))
            recipe_row = cursor.fetchone()
            if not recipe_row:
                raise HTTPException(status_code=404, detail="Recipe not found")
            
            cursor.execute("SELECT comment FROM comments WHERE recipe_id = ?", (recipeId,))
            comments = [row['comment'] for row in cursor.fetchall()]
            
            cursor.execute("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", (recipeId,))
            avg_rating = cursor.fetchone()[0]
            
            # Escape all user-generated content for HTML output
            recipe_data = {
                "id": escape(str(recipe_row['id'])),
                "title": escape(recipe_row['title']),
                "ingredients": [escape(ing) for ing in json.loads(recipe_row['ingredients'])],
                "instructions": escape(recipe_row['instructions']),
                "comments": [escape(c) for c in comments],
                "avg_rating": avg_rating
            }
            
        template = Template(DETAIL_TEMPLATE)
        return template.render(recipe=recipe_data)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/recipes/{recipeId}/comments", status_code=201)
async def add_comment(recipeId: str, request: Request):
    if not recipeId.isdigit():
        raise HTTPException(status_code=404, detail="Recipe not found")

    content_type = request.headers.get('content-type', '')
    try:
        if 'application/json' in content_type:
            data = await request.json()
            comment_text = data.get('comment')
        else:
            form_data = await request.form()
            comment_text = form_data.get('comment')

        if not comment_text or not isinstance(comment_text, str):
            raise HTTPException(status_code=400, detail="Invalid input")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Recipe not found")
            
            cursor.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipeId, comment_text))
            conn.commit()
        
        return Response(status_code=201)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

@app.post("/recipes/{recipeId}/ratings", status_code=201)
async def add_rating(recipeId: str, request: Request):
    if not recipeId.isdigit():
        raise HTTPException(status_code=404, detail="Recipe not found")

    content_type = request.headers.get('content-type', '')
    try:
        if 'application/json' in content_type:
            data = await request.json()
            rating_val = data.get('rating')
        else:
            form_data = await request.form()
            rating_val = form_data.get('rating')

        try:
            rating_val = int(rating_val)
            if not (1 <= rating_val <= 5):
                raise ValueError()
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid input")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Recipe not found")
            
            cursor.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipeId, rating_val))
            conn.commit()
        
        return Response(status_code=201)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)