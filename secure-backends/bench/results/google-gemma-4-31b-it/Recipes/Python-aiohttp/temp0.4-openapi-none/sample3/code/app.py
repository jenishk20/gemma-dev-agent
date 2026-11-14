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

    async def execute(self, query, params=()):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_sync, query, params)

    def _execute_sync(self, query, params):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()

    async def fetch_one(self, query, params=()):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_one_sync, query, params)

    def _fetch_one_sync(self, query, params):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()

db = Database()

# --- Handlers ---

async def get_recipes_overview(request):
    # Retrieve recipes and their average ratings
    query = """
        SELECT r.id, r.title, AVG(rt.rating) as avgRating 
        FROM recipes r 
        LEFT JOIN ratings rt ON r.id = rt.recipe_id 
        GROUP BY r.id 
        ORDER BY avgRating DESC, r.id DESC
    """
    rows = await db.execute(query)
    
    html = "<h1>Recipe Overview</h1><ul>"
    for row in rows:
        rid, title, avg = row
        avg_str = f"{avg:.1f}" if avg else "No ratings"
        html += f'<li><a href="/recipes/{rid}">{title}</a> (Rating: {avg_str})</li>'
    html += "</ul>"
    
    return web.Response(text=html, content_type='text/html')

async def upload_recipe(request):
    try:
        data = await request.json()
        title = data.get('title')
        ingredients = data.get('ingredients')
        instructions = data.get('instructions')

        if not all([title, ingredients, instructions]):
            return web.Response(status=400, text="Missing required fields")

        recipe_id = str(uuid.uuid4())
        # Store ingredients as JSON string
        await db.execute(
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

async def get_recipe_detail(request):
    recipe_id = request.match_info.get('recipeId')
    recipe = await db.fetch_one("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    
    if not recipe:
        return web.Response(status=404, text="Recipe not found")

    comments_rows = await db.execute("SELECT comment FROM comments WHERE recipe_id = ?", (recipe_id,))
    ratings_rows = await db.execute("SELECT rating FROM ratings WHERE recipe_id = ?", (recipe_id,))
    
    avg_rating = None
    if ratings_rows:
        avg_rating = sum(r[0] for r in ratings_rows) / len(ratings_rows)

    # The schema asks for text/html for this endpoint
    html = f"<h1>{recipe['title']}</h1>"
    html += f"<p><strong>Ingredients:</strong> {recipe['ingredients']}</p>"
    html += f"<p><strong>Instructions:</strong> {recipe['instructions']}</p>"
    html += f"<p><strong>Average Rating:</strong> {avg_rating if avg_rating else 'N/A'}</p>"
    html += "<h3>Comments</h3><ul>"
    for c in comments_rows:
        html += f"<li>{c[0]}</li>"
    html += "</ul><br><a href='/recipes'>Back to overview</a>"
    
    return web.Response(text=html, content_type='text/html')

async def add_comment(request):
    recipe_id = request.match_info.get('recipeId')
    recipe = await db.fetch_one("SELECT id FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        return web.Response(status=404, text="Recipe not found")

    try:
        data = await request.json()
        comment = data.get('comment')
        if not comment:
            return web.Response(status=400, text="Comment is required")
        
        await db.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipe_id, comment))
        return web.Response(status=201)
    except Exception:
        return web.Response(status=400, text="Invalid input")

async def add_rating(request):
    recipe_id = request.match_info.get('recipeId')
    recipe = await db.fetch_one("SELECT id FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        return web.Response(status=404, text="Recipe not found")

    try:
        data = await request.json()
        rating = data.get('rating')
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            return web.Response(status=400, text="Rating must be an integer between 1 and 5")
        
        await db.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipe_id, rating))
        return web.Response(status=201)
    except Exception:
        return web.Response(status=400, text="Invalid input")

# --- App Setup ---

app = web.Application()
app.add_routes([
    web.get('/recipes', get_recipes_overview),
    web.post('/recipes/upload', upload_recipe),
    web.get('/recipes/{recipeId}', get_recipe_detail),
    web.post('/recipes/{recipeId}/comments', add_comment),
    web.post('/recipes/{recipeId}/ratings', add_rating),
])

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)