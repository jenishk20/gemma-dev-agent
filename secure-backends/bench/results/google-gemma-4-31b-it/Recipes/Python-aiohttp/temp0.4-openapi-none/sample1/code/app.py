import asyncio
import json
import sqlite3
import uuid
from aiohttp import web

# Database initialization
def init_db():
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            ingredients TEXT NOT NULL,
            instructions TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id TEXT,
            comment TEXT NOT NULL,
            FOREIGN KEY(recipe_id) REFERENCES recipes(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id TEXT,
            rating INTEGER NOT NULL,
            FOREIGN KEY(recipe_id) REFERENCES recipes(id)
        )
    ''')
    conn.commit()
    conn.close()

def db_query(query, params=(), fetchall=True):
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute(query, params)
    if fetchall:
        res = cursor.fetchall()
    else:
        res = cursor.fetchone()
    conn.commit()
    conn.close()
    return res

# Handlers
async def get_recipes_overview(request):
    # Fetch recipes and their average ratings
    query = '''
        SELECT r.id, r.title, AVG(rt.rating) as avg_rating 
        FROM recipes r 
        LEFT JOIN ratings rt ON r.id = rt.recipe_id 
        GROUP BY r.id 
        ORDER BY avg_rating DESC, r.id DESC
    '''
    rows = db_query(query)
    
    html = "<html><body><h1>Recipe Overview</h1><ul>"
    for row in rows:
        recipe_id, title, avg_rating = row
        rating_str = f"{avg_rating:.1f}" if avg_rating else "No ratings"
        html += f'<li><a href="/recipes/{recipe_id}">{title}</a> (Rating: {rating_str})</li>'
    html += "</ul></body></html>"
    
    return web.Response(text=html, content_type='text/html')

async def upload_recipe(request):
    try:
        data = await request.json()
        title = data.get('title')
        ingredients = data.get('ingredients')
        instructions = data.get('instructions')

        if not all([title, ingredients, instructions]):
            return web.json_response({'error': 'Missing required fields'}, status=400)

        recipe_id = str(uuid.uuid4())
        # Store ingredients as JSON string
        db_query('INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)', 
                 (recipe_id, title, json.dumps(ingredients), instructions), fetchall=False)

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
    recipe_id = request.match_info.get('recipeId')
    recipe = db_query('SELECT id, title, ingredients, instructions FROM recipes WHERE id = ?', (recipe_id,), fetchall=False)
    
    if not recipe:
        return web.Response(text="Recipe not found", status=404)

    comments = db_query('SELECT comment FROM comments WHERE recipe_id = ?', (recipe_id,))
    ratings = db_query('SELECT rating FROM ratings WHERE recipe_id = ?', (recipe_id,))
    
    avg_rating = sum(r[0] for r in ratings) / len(ratings) if ratings else None
    ingredients = json.loads(recipe[2])

    html = f"""
    <html><body>
        <h1>{recipe[1]}</h1>
        <p><strong>Ingredients:</strong> {', '.join(ingredients)}</p>
        <p><strong>Instructions:</strong> {recipe[3]}</p>
        <p><strong>Average Rating:</strong> {avg_rating if avg_rating else 'N/A'}</p>
        <h3>Comments</h3>
        <ul>"""
    for c in comments:
        html += f"<li>{c[0]}</li>"
    html += "</ul><a href='/recipes'>Back to Overview</a></body></html>"
    
    return web.Response(text=html, content_type='text/html')

async def add_comment(request):
    recipe_id = request.match_info.get('recipeId')
    try:
        data = await request.json()
        comment = data.get('comment')
        if not comment:
            return web.json_response({'error': 'Comment is required'}, status=400)
        
        # Check if recipe exists
        if not db_query('SELECT id FROM recipes WHERE id = ?', (recipe_id,), fetchall=False):
            return web.Response(status=404)

        db_query('INSERT INTO comments (recipe_id, comment) VALUES (?, ?)', (recipe_id, comment), fetchall=False)
        return web.Response(status=201)
    except Exception:
        return web.json_response({'error': 'Invalid input'}, status=400)

async def add_rating(request):
    recipe_id = request.match_info.get('recipeId')
    try:
        data = await request.json()
        rating = data.get('rating')
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            return web.json_response({'error': 'Rating must be an integer between 1 and 5'}, status=400)
        
        if not db_query('SELECT id FROM recipes WHERE id = ?', (recipe_id,), fetchall=False):
            return web.Response(status=404)

        db_query('INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)', (recipe_id, rating), fetchall=False)
        return web.Response(status=201)
    except Exception:
        return web.json_response({'error': 'Invalid input'}, status=400)

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