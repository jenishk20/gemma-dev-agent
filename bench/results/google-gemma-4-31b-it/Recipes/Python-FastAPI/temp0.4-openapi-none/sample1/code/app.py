import sqlite3
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Recipe Sharing App API")

# --- Database Setup ---
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
                FOREIGN KEY(recipe_id) REFERENCES recipes(id)
            )
        ''')
        # Ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                FOREIGN KEY(recipe_id) REFERENCES recipes(id)
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

class Comment(BaseModel):
    comment: str

class Recipe(BaseModel):
    id: str
    title: str
    ingredients: List[str]
    instructions: str
    comments: List[Comment]
    avgRating: Optional[float]

# --- Helper Functions ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- API Endpoints ---

@app.get("/recipes", response_class=HTMLResponse)
async def get_recipes_overview():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Get recipes and their average ratings
    query = '''
        SELECT r.id, r.title, AVG(rt.rating) as avg_rating 
        FROM recipes r 
        LEFT JOIN ratings rt ON r.id = rt.recipe_id 
        GROUP BY r.id 
        ORDER BY avg_rating DESC, r.id DESC
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    html_content = "<h1>Recipe Overview</h1><ul>"
    for row in rows:
        rating_text = f" (Rating: {row['avg_rating']:.1f})" if row['avg_rating'] else " (No ratings)"
        html_content += f'<li><a href="/recipes/{row["id"]}">{row["title"]}</a>{rating_text}</li>'
    html_content += "</ul>"
    return html_content

@app.post("/recipes/upload", status_code=201, response_model=Recipe)
async def upload_recipe(recipe: RecipeCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    ingredients_json = json.dumps(recipe.ingredients)
    cursor.execute(
        "INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)",
        (recipe.title, ingredients_json, recipe.instructions)
    )
    recipe_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Fetch the created recipe to return it
    return await get_recipe_data(str(recipe_id))

@app.get("/recipes/{recipeId}", response_class=HTMLResponse)
async def get_recipe(recipeId: str):
    recipe_data = await get_recipe_data(recipeId)
    
    html_content = f"""
    <h1>{recipe_data.title}</h1>
    <p><strong>Average Rating:</strong> {recipe_data.avgRating if recipe_data.avgRating else 'N/A'}</p>
    <h3>Ingredients</h3>
    <ul>{''.join([f'<li>{i}</li>' for i in recipe_data.ingredients])}</ul>
    <h3>Instructions</h3>
    <p>{recipe_data.instructions}</p>
    <h3>Comments</h3>
    <ul>{''.join([f'<li>{c.comment}</li>' for c in recipe_data.comments])}</ul>
    <hr>
    <h4>Add a Comment</h4>
    <form action="/recipes/{recipeId}/comments" method="post">
        <input type="hidden" name="comment_json" value='{{"comment": ""}}'> 
        <input type="text" name="comment_text" placeholder="Your comment">
        <input type="submit" value="Post Comment">
    </form>
    <h4>Rate this Recipe</h4>
    <form action="/recipes/{recipeId}/ratings" method="post">
        <input type="number" name="rating_val" min="1" max="5">
        <input type="submit" value="Submit Rating">
    </form>
    <br><a href="/recipes">Back to Overview</a>
    """
    # Note: The HTML forms above are simplified; for the API to work, 
    # the client should send JSON as per the OpenAPI spec.
    return html_content

@app.post("/recipes/{recipeId}/comments", status_code=201)
async def add_comment(recipeId: str, payload: CommentCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if recipe exists
    cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    cursor.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipeId, payload.comment))
    conn.commit()
    conn.close()
    return Response(status_code=201)

@app.post("/recipes/{recipeId}/ratings", status_code=201)
async def add_rating(recipeId: str, payload: RatingCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if recipe exists
    cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    cursor.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipeId, payload.rating))
    conn.commit()
    conn.close()
    return Response(status_code=201)

async def get_recipe_data(recipeId: str) -> Recipe:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipeId,))
    recipe_row = cursor.fetchone()
    if not recipe_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    cursor.execute("SELECT comment FROM comments WHERE recipe_id = ?", (recipeId,))
    comments = [Comment(comment=row['comment']) for row in cursor.fetchall()]
    
    cursor.execute("SELECT AVG(rating) as avg FROM ratings WHERE recipe_id = ?", (recipeId,))
    avg_rating_row = cursor.fetchone()
    avg_rating = avg_rating_row['avg'] if avg_rating_row['avg'] is not None else None
    
    conn.close()
    
    return Recipe(
        id=str(recipe_row['id']),
        title=recipe_row['title'],
        ingredients=json.loads(recipe_row['ingredients']),
        instructions=recipe_row['instructions'],
        comments=comments,
        avgRating=avg_rating
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)