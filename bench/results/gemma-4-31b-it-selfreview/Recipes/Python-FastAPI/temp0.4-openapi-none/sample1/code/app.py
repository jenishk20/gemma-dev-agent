import sqlite3
import json
import html
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Recipe Sharing App API")

# --- Database Setup ---
DB_PATH = "db.sqlite3"

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
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
                    FOREIGN KEY(recipe_id) REFERENCES recipes(id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipe_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    FOREIGN KEY(recipe_id) REFERENCES recipes(id)
                )
            ''')
            conn.commit()
    except Exception:
        # In a real app, we would log this. Here we ensure the app doesn't crash during init.
        pass

init_db()

# --- Pydantic Models ---
class RecipeCreate(BaseModel):
    title: str = Field(..., max_length=1000)
    ingredients: List[str] = Field(..., max_items=100)
    instructions: str = Field(..., max_length=10000)

class CommentCreate(BaseModel):
    comment: str = Field(..., max_length=1000)

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

def safe_html_escape(text: any) -> str:
    """Escapes content for safe HTML rendering to prevent XSS."""
    if text is None:
        return ""
    return html.escape(str(text))

# --- API Endpoints ---

@app.get("/recipes", response_class=HTMLResponse)
async def get_recipes_overview():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Parameterized query (though no user input here)
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
            # Escape title to prevent XSS
            safe_title = safe_html_escape(row['title'])
            safe_id = safe_html_escape(str(row['id']))
            rating_text = f" (Rating: {row['avg_rating']:.1f})" if row['avg_rating'] else " (No ratings)"
            html_content += f'<li><a href="/recipes/{safe_id}">{safe_title}</a>{rating_text}</li>'
        html_content += "</ul>"
        return html_content
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/recipes/upload", status_code=201, response_model=Recipe)
async def upload_recipe(recipe: RecipeCreate):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # JSON serialization is safe; we use parameterized query for SQL injection prevention
        ingredients_json = json.dumps(recipe.ingredients)
        cursor.execute(
            "INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)",
            (recipe.title, ingredients_json, recipe.instructions)
        )
        recipe_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return await get_recipe_data(str(recipe_id))
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail="Invalid input")

@app.get("/recipes/{recipeId}", response_class=HTMLResponse)
async def get_recipe(recipeId: str):
    # Validate that recipeId is numeric to prevent unexpected input types
    if not recipeId.isdigit():
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    recipe_data = await get_recipe_data(recipeId)
    
    # Escape all user-generated content to prevent XSS
    safe_title = safe_html_escape(recipe_data.title)
    safe_instructions = safe_html_escape(recipe_data.instructions)
    safe_ingredients = [safe_html_escape(i) for i in recipe_data.ingredients]
    safe_comments = [safe_html_escape(c.comment) for c in recipe_data.comments]
    safe_id = safe_html_escape(recipeId)
    
    avg_rating = recipe_data.avgRating if recipe_data.avgRating is not None else 'N/A'
    
    html_content = f"""
    <h1>{safe_title}</h1>
    <p><strong>Average Rating:</strong> {safe_html_escape(avg_rating)}</p>
    <h3>Ingredients</h3>
    <ul>{''.join([f'<li>{i}</li>' for i in safe_ingredients])}</ul>
    <h3>Instructions</h3>
    <p>{safe_instructions}</p>
    <h3>Comments</h3>
    <ul>{''.join([f'<li>{c}</li>' for c in safe_comments])}</ul>
    <hr>
    <a href="/recipes">Back to Overview</a>
    """
    return html_content

@app.post("/recipes/{recipeId}/comments", status_code=201)
async def add_comment(recipeId: str, payload: CommentCreate):
    if not recipeId.isdigit():
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipeId, payload.comment))
        conn.commit()
        conn.close()
        return Response(status_code=201)
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail="Invalid input")

@app.post("/recipes/{recipeId}/ratings", status_code=201)
async def add_rating(recipeId: str, payload: RatingCreate):
    if not recipeId.isdigit():
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        cursor.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipeId, payload.rating))
        conn.commit()
        conn.close()
        return Response(status_code=201)
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail="Invalid input")

async def get_recipe_data(recipeId: str) -> Recipe:
    if not recipeId.isdigit():
        raise HTTPException(status_code=404, detail="Recipe not found")
        
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