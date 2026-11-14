import asyncio
import sqlite3
import json
from aiohttp import web

# Database helper to handle synchronous sqlite3 calls in a thread pool
async def run_query(query, params=(), fetch=False, commit=False):
    def _execute():
        with sqlite3.connect('db.sqlite3') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            if fetch:
                return [dict(row) for row in cursor.fetchall()]
            return cursor.lastrowid

    return await asyncio.to_thread(_execute)

async def init_db():
    await run_query('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            ingredients TEXT NOT NULL,
            instructions TEXT NOT NULL
        )
    ''', commit=True)
    await run_query('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER,
            comment TEXT NOT NULL,
            FOREIGN KEY(recipe_id) REFERENCES recipes(id)
        )
    ''', commit=True)
    await run_query('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER,
            rating INTEGER NOT NULL,
            FOREIGN KEY(recipe_id) REFERENCES recipes(id)
        )
    ''', commit=True)

# Handlers
async def get_recipes_overview(request):
    recipes = await run_query("SELECT id, title FROM recipes", fetch=True)
    
    html = "<html><body><h1>Recipe Overview</h1><ul>"
    for r in recipes:
        html += f'<li><a href="/recipes/{r["id"]}">{r["title"]}</a></li>'
    html += "</ul></body></html>"
    
    return web.Response(text=html, content_type='text/html')

async def upload_recipe(request):
    try:
        data = await request.json()
        title = data.get('title')
        ingredients = data.get('ingredients')
        instructions = data.get('instructions')

        if not all([title, ingredients, instructions]):
            return web.Response(status=400, text="Missing required fields")

        # Store ingredients as JSON string
        recipe_id = await run_query(
            "INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)",
            (title, json.dumps(ingredients), instructions),
            commit=True
        )

        return web.json_response({
            "id": str(recipe_id),
            "title": title,
            "ingredients": ingredients,
            "instructions": instructions,
            "comments": [],
            "avgRating": None
        }, status=201)
    except Exception:
        return web.Response(status=400, text="Invalid input")

async def get_recipe_detail(request):
    recipe_id = request.match_info.get('recipeId')
    recipe = await run_query("SELECT * FROM recipes WHERE id = ?", (recipe_id,), fetch=True)
    
    if not recipe:
        return web.Response(status=404, text="Recipe not found")
    
    r = recipe[0]
    comments = await run_query("SELECT comment FROM comments WHERE recipe_id = ?", (recipe_id,), fetch=True)
    ratings = await run_query("SELECT rating FROM ratings WHERE recipe_id = ?", (recipe_id,), fetch=True)
    
    avg_rating = sum(rt['rating'] for rt in ratings) / len(ratings) if ratings else "N/A"
    ingredients = json.loads(r['ingredients'])
    
    html = f"<html><body><h1>{r['title']}</h1>"
    html += f"<h3>Ingredients</h3><ul>"
    for ing in ingredients:
        html += f"<li>{ing}</li>"
    html += f"</ul><h3>Instructions</h3><p>{r['instructions']}</p>"
    html += f"<h3>Average Rating: {avg_rating}</h3>"
    html += "<h3>Comments</h3><ul>"
    for c in comments:
        html += f"<li>{c['comment']}</li>"
    html += "</ul><br><a href='/recipes'>Back to overview</a></body></html>"
    
    return web.Response(text=html, content_type='text/html')

async def add_comment(request):
    recipe_id = request.match_info.get('recipeId')
    try:
        data = await request.json()
        comment_text = data.get('comment')
        if not comment_text:
            return web.Response(status=400, text="Comment is required")
        
        # Check if recipe exists
        recipe = await run_query("SELECT id FROM recipes WHERE id = ?", (recipe_id,), fetch=True)
        if not recipe:
            return web.Response(status=404, text="Recipe not found")
            
        await run_query("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipe_id, comment_text), commit=True)
        return web.Response(status=201)
    except Exception:
        return web.Response(status=400, text="Invalid input")

async def add_rating(request):
    recipe_id = request.match_info.get('recipeId')
    try:
        data = await request.json()
        rating = data.get('rating')
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            return web.Response(status=400, text="Rating must be an integer between 1 and 5")
        
        recipe = await run_query("SELECT id FROM recipes WHERE id = ?", (recipe_id,), fetch=True)
        if not recipe:
            return web.Response(status=404, text="Recipe not found")
            
        await run_query("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipe_id, rating), commit=True)
        return web.Response(status=201)
    except Exception:
        return web.Response(status=400, text="Invalid input")

app = web.Application()
app.add_routes([
    web.get('/recipes', get_recipes_overview),
    web.post('/recipes/upload', upload_recipe),
    web.get('/recipes/{recipeId}', get_recipe_detail),
    web.post('/recipes/{recipeId}/comments', add_comment),
    web.post('/recipes/{recipeId}/ratings', add_rating),
])

if __name__ == '__main__':
    # Initialize DB before starting server
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    web.run_app(app, host='0.0.0.0', port=5000)