import asyncio
import json
import sqlite3
import uuid
from aiohttp import web

# Database initialization
DB_NAME = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_NAME)
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
            FOREIGN KEY(recipe_id) REFERENCES recipes(id)
        )
    ''')
    # Ratings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            FOREIGN KEY(recipe_id) REFERENCES recipes(id)
        )
    ''')
    conn.commit()
    conn.close()

def db_query(query, params=(), fetchall=True):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchall() if fetchall else cursor.fetchone()
    conn.commit()
    conn.close()
    return res

# Route Handlers

async def get_recipes_overview(request):
    """GET /recipes - HTML overview of recipes"""
    recipes = db_query("SELECT id, title FROM recipes")
    
    html = "<h1>Recipe Overview</h1><ul>"
    for r_id, title in recipes:
        html += f'<li><a href="/recipes/{r_id}">{title}</a></li>'
    html += "</ul>"
    
    return web.Response(text=html, content_type='text/html')

async def upload_recipe(request):
    """POST /recipes/upload - Create a new recipe"""
    try:
        data = await request.json()
        title = data.get('title')
        ingredients = data.get('ingredients')
        instructions = data.get('instructions')

        if not all([title, ingredients, instructions]):
            return web.json_response({'error': 'Missing required fields'}, status=400)

        recipe_id = str(uuid.uuid4())
        # Store ingredients as JSON string in SQLite
        db_query("INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)", 
                 (recipe_id, title, json.dumps(ingredients), instructions))

        return web.json_response({
            'id': recipe_id,
            'title': title,
            'ingredients': ingredients,
            'instructions': instructions,
            'comments': [],
            'avgRating': None
        }, status=201)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=400)

async def get_recipe_detail(request):
    """GET /recipes/{recipeId} - HTML detail of a recipe"""
    recipe_id = request.match_info.get('recipeId')
    recipe = db_query("SELECT title, ingredients, instructions FROM recipes WHERE id = ?", (recipe_id,), fetchall=False)
    
    if not recipe:
        return web.Response(text="Recipe not found", status=404)

    title, ingredients_json, instructions = recipe
    ingredients = json.loads(ingredients_json)
    
    comments = db_query("SELECT comment FROM comments WHERE recipe_id = ?", (recipe_id,))
    ratings = db_query("SELECT rating FROM ratings WHERE recipe_id = ?", (recipe_id,))
    
    avg_rating = sum(r[0] for r in ratings) / len(ratings) if ratings else "No ratings yet"

    html = f"<h1>{title}</h1>"
    html += f"<h3>Ingredients</h3><ul>"
    for ing in ingredients:
        html += f"<li>{ing}</li>"
    html += "</ul>"
    html += f"<h3>Instructions</h3><p>{instructions}</p>"
    html += f"<h3>Average Rating: {avg_rating}</h3>"
    html += "<h3>Comments</h3><ul>"
    for c in comments:
        html += f"<li>{c[0]}</li>"
    html += "</ul>"
    html += '<br><a href="/recipes">Back to overview</a>'
    
    return web.Response(text=html, content_type='text/html')

async def add_comment(request):
    """POST /recipes/{recipeId}/comments - Add comment"""
    recipe_id = request.match_info.get('recipeId')
    
    # Verify recipe exists
    recipe = db_query("SELECT id FROM recipes WHERE id = ?", (recipe_id,), fetchall=False)
    if not recipe:
        return web.Response(status=404)

    try:
        data = await request.json()
        comment = data.get('comment')
        if not comment:
            return web.json_response({'error': 'Comment is required'}, status=400)
        
        db_query("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipe_id, comment))
        return web.Response(status=201)
    except Exception:
        return web.json_response({'error': 'Invalid input'}, status=400)

async def add_rating(request):
    """POST /recipes/{recipeId}/ratings - Add rating"""
    recipe_id = request.match_info.get('recipeId')
    
    recipe = db_query("SELECT id FROM recipes WHERE id = ?", (recipe_id,), fetchall=False)
    if not recipe:
        return web.Response(status=404)

    try:
        data = await request.json()
        rating = data.get('rating')
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            return web.json_response({'error': 'Rating must be an integer between 1 and 5'}, status=400)
        
        db_query("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipe_id, rating))
        return web.Response(status=201)
    except Exception:
        return web.json_response({'error': 'Invalid input'}, status=400)

# App Setup
app = web.Application()
app.add_routes([
    web.get('/recipes', get_recipes_overview),
    web.post('/recipes/upload', upload_recipe),
    web.get('/recipes/{recipeId}', get_recipe_detail),
    web.post('/recipes/{recipeId}/comments', add_comment),
    web.post('/recipes/{recipeId}/ratings', add_rating),
])

if __name__ == '__main__':
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)