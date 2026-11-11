import asyncio
import json
import sqlite3
import uuid
from aiohttp import web

# Database helper to handle synchronous sqlite3 calls in an async environment
class Database:
    def __init__(self, db_path="db.sqlite3"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
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

    def run_query(self, query, params=(), fetch=False):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()
            return cursor.lastrowid

db = Database()

def get_recipe_html(recipe_id):
    # Simple HTML generator for the recipe detail page
    recipe_data = db.run_query("SELECT title, ingredients, instructions FROM recipes WHERE id = ?", (recipe_id,), fetch=True)
    if not recipe_data:
        return None
    
    title, ingredients_json, instructions = recipe_data[0]
    ingredients = json.loads(ingredients_json)
    
    comments_data = db.run_query("SELECT comment FROM comments WHERE recipe_id = ?", (recipe_id,), fetch=True)
    ratings_data = db.run_query("SELECT rating FROM ratings WHERE recipe_id = ?", (recipe_id,), fetch=True)
    
    avg_rating = 0
    if ratings_data:
        avg_rating = sum(r[0] for r in ratings_data) / len(ratings_data)

    ingredients_list = "".join([f"<li>{i}</li>" for i in ingredients])
    comments_list = "".join([f"<li>{c[0]}</li>" for c in comments_data])
    
    return f"""
    <html>
        <body>
            <h1>{title}</h1>
            <h3>Ingredients</h3>
            <ul>{ingredients_list}</ul>
            <h3>Instructions</h3>
            <p>{instructions}</p>
            <h3>Average Rating: {avg_rating:.1f}</h3>
            <h3>Comments</h3>
            <ul>{comments_list}</ul>
            <a href="/recipes">Back to Overview</a>
        </body>
    </html>
    """

async def handle_get_recipes(request):
    # Retrieve all recipes for the overview page
    recipes = db.run_query("SELECT id, title FROM recipes", fetch=True)
    links = "".join([f'<li><a href="/recipes/{r[0]}">{r[1]}</a></li>' for r in recipes])
    html = f"<html><body><h1>Recipe Overview</h1><ul>{links}</ul></body></html>"
    return web.Response(text=html, content_type='text/html')

async def handle_upload_recipe(request):
    try:
        data = await request.json()
        title = data.get('title')
        ingredients = data.get('ingredients')
        instructions = data.get('instructions')

        if not all([title, ingredients, instructions]):
            return web.Response(status=400, text="Missing required fields")

        recipe_id = str(uuid.uuid4())
        db.run_query(
            "INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)",
            (recipe_id, title, json.dumps(ingredients), instructions)
        )

        response_data = {
            "id": recipe_id,
            "title": title,
            "ingredients": ingredients,
            "instructions": instructions,
            "comments": [],
            "avgRating": None
        }
        return web.json_response(response_data, status=201)
    except Exception:
        return web.Response(status=400, text="Invalid input")

async def handle_get_recipe(request):
    recipe_id = request.match_info.get('recipeId')
    html = get_recipe_html(recipe_id)
    if html:
        return web.Response(text=html, content_type='text/html')
    return web.Response(status=404, text="Recipe not found")

async def handle_post_comment(request):
    recipe_id = request.match_info.get('recipeId')
    # Check if recipe exists
    exists = db.run_query("SELECT 1 FROM recipes WHERE id = ?", (recipe_id,), fetch=True)
    if not exists:
        return web.Response(status=404, text="Recipe not found")

    try:
        data = await request.json()
        comment = data.get('comment')
        if not comment:
            return web.Response(status=400, text="Comment is required")
        
        db.run_query("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipe_id, comment))
        return web.Response(status=201)
    except Exception:
        return web.Response(status=400, text="Invalid input")

async def handle_post_rating(request):
    recipe_id = request.match_info.get('recipeId')
    exists = db.run_query("SELECT 1 FROM recipes WHERE id = ?", (recipe_id,), fetch=True)
    if not exists:
        return web.Response(status=404, text="Recipe not found")

    try:
        data = await request.json()
        rating = data.get('rating')
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            return web.Response(status=400, text="Rating must be an integer between 1 and 5")
        
        db.run_query("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipe_id, rating))
        return web.Response(status=201)
    except Exception:
        return web.Response(status=400, text="Invalid input")

app = web.Application()
app.add_routes([
    web.get('/recipes', handle_get_recipes),
    web.post('/recipes/upload', handle_upload_recipe),
    web.get('/recipes/{recipeId}', handle_get_recipe),
    web.post('/recipes/{recipeId}/comments', handle_post_comment),
    web.post('/recipes/{recipeId}/ratings', handle_post_rating),
])

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)