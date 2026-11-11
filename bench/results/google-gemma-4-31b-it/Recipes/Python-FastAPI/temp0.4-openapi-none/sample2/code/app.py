import sqlite3
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Recipe Sharing App API")

DB_FILE = "db.sqlite3"

# --- Database Setup ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
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
                rating INTEGER NOT NULL,
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

# --- Helper Functions ---
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Routes ---

@app.get("/recipes", response_class=HTMLResponse)
async def get_recipes_overview():
    conn = get_db()
    cursor = conn.cursor()
    # Get recipes sorted by average rating descending
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

    html_content = "<h1>Recipe Overview</h1><ul>"
    for row in recipes:
        html_content += f'<li><a href="/recipes/{row["id"]}">{row["title"]}</a> (Rating: {row["avg_rating"] or "N/A"})</li>'
    html_content += "</ul>"
    return HTMLResponse(content=html_content)

@app.post("/recipes/upload", status_code=201, response_model=RecipeSchema)
async def upload_recipe(recipe: RecipeCreate):
    conn = get_db()
    cursor = conn.cursor()
    ingredients_json = json.dumps(recipe.ingredients)
    cursor.execute(
        "INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)",
        (recipe.title, ingredients_json, recipe.instructions)
    )
    recipe_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Return the created recipe object as per schema
    return RecipeSchema(
        id=str(recipe_id),
        title=recipe.title,
        ingredients=recipe.ingredients,
        instructions=recipe.instructions,
        comments=[],
        avgRating=None
    )

@app.get("/recipes/{recipeId}", response_class=HTMLResponse)
async def get_recipe(recipeId: str):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipeId,))
    recipe_row = cursor.fetchone()
    if not recipe_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Recipe not found")

    cursor.execute("SELECT comment FROM comments WHERE recipe_id = ?", (recipeId,))
    comments = cursor.fetchall()
    
    cursor.execute("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", (recipeId,))
    avg_rating = cursor.fetchone()[0]
    conn.close()

    ingredients = json.loads(recipe_row["ingredients"])
    ing_list = "".join([f"<li>{i}</li>" for i in ingredients])
    com_list = "".join([f"<li>{c['comment']}</li>" for c in comments])

    html_content = f"""
    <h1>{recipe_row['title']}</h1>
    <p><strong>Average Rating:</strong> {avg_rating or 'No ratings yet'}</p>
    <h3>Ingredients</h3>
    <ul>{ing_list}</ul>
    <h3>Instructions</h3>
    <p>{recipe_row['instructions']}</p>
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

@app.post("/recipes/{recipeId}/comments", status_code=201)
async def add_comment(recipeId: str, payload: CommentCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    cursor.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipeId, payload.comment))
    conn.commit()
    conn.close()
    return {"message": "Comment added successfully"}

@app.post("/recipes/{recipeId}/ratings", status_code=201)
async def add_rating(recipeId: str, payload: RatingCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    cursor.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipeId, payload.rating))
    conn.commit()
    conn.close()
    return {"message": "Rating added successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)