import sqlite3
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template

app = FastAPI(title="Recipe Sharing App API")

DB_FILE = "db.sqlite3"

# --- Database Setup ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
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

# --- Pydantic Models ---
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

# --- HTML Templates ---
INDEX_TEMPLATE = """
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
"""

RECIPE_TEMPLATE = """
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
    <ul>{% for c in recipe.comments %}<li>{{ c }}</li>{% endfor %}</ul>
    
    <hr>
    <h4>Add a Comment</h4>
    <form action="/recipes/{{ recipe.id }}/comments" method="post">
        <input type="text" name="comment" required>
        <button type="submit">Post</button>
    </form>
    
    <h4>Rate this Recipe</h4>
    <form action="/recipes/{{ recipe.id }}/ratings" method="post">
        <input type="number" name="rating" min="1" max="5" required>
        <button type="submit">Rate</button>
    </form>
    <br>
    <a href="/recipes">Back to Overview</a>
</body>
</html>
"""

# --- API Endpoints ---

@app.get("/recipes", response_class=HTMLResponse)
async def get_recipes_overview():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Get recipes and their average ratings
        query = '''
            SELECT r.id, r.title, AVG(rt.rating) as avg_rating 
            FROM recipes r 
            LEFT JOIN ratings rt ON r.id = rt.recipe_id 
            GROUP BY r.id 
            ORDER BY avg_rating DESC
        '''
        cursor.execute(query)
        recipes = cursor.fetchall()
    
    template = Template(INDEX_TEMPLATE)
    return template.render(recipes=recipes)

@app.post("/recipes/upload", status_code=201, response_model=RecipeSchema)
async def upload_recipe(recipe: RecipeCreate):
    recipe_id = str(uuid.uuid4())
    ingredients_str = ",".join(recipe.ingredients)
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
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
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get recipe
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipeId,))
        recipe_row = cursor.fetchone()
        if not recipe_row:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        # Get comments
        cursor.execute("SELECT comment FROM comments WHERE recipe_id = ?", (recipeId,))
        comments = [row['comment'] for row in cursor.fetchall()]
        
        # Get average rating
        cursor.execute("SELECT AVG(rating) as avg_rating FROM ratings WHERE recipe_id = ?", (recipeId,))
        rating_row = cursor.fetchone()
        avg_rating = rating_row['avg_rating']
        
        recipe_data = {
            "id": recipe_row['id'],
            "title": recipe_row['title'],
            "ingredients": recipe_row['ingredients'].split(','),
            "instructions": recipe_row['instructions'],
            "comments": comments,
            "avg_rating": avg_rating
        }
    
    template = Template(RECIPE_TEMPLATE)
    return template.render(recipe=recipe_data)

@app.post("/recipes/{recipeId}/comments", status_code=201)
async def add_comment(recipeId: str, request: Request):
    # Support both JSON and Form data for the HTML template
    content_type = request.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        try:
            body = await request.json()
            comment_text = body.get('comment')
        except:
            raise HTTPException(status_code=400, detail="Invalid JSON")
    else:
        form_data = await request.form()
        comment_text = form_data.get('comment')

    if not comment_text:
        raise HTTPException(status_code=400, detail="Comment is required")

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipeId, comment_text))
        conn.commit()
    
    return Response(status_code=201)

@app.post("/recipes/{recipeId}/ratings", status_code=201)
async def add_rating(recipeId: str, request: Request):
    content_type = request.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        try:
            body = await request.json()
            rating_val = body.get('rating')
        except:
            raise HTTPException(status_code=400, detail="Invalid JSON")
    else:
        form_data = await request.form()
        rating_val = form_data.get('rating')

    try:
        rating_val = int(rating_val)
        if not (1 <= rating_val <= 5):
            raise ValueError()
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Rating must be an integer between 1 and 5")

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipeId, rating_val))
        conn.commit()
    
    return Response(status_code=201)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)