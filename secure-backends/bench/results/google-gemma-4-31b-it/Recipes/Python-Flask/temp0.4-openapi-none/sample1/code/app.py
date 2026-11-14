import sqlite3
import json
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_NAME = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
        conn.commit()

# HTML Templates for the responses specified in the OpenAPI schema
OVERVIEW_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Recipe Overview</title></head>
<body>
    <h1>Recent and Top-Rated Recipes</h1>
    <ul>
        {% for recipe in recipes %}
        <li>
            <a href="/recipes/{{ recipe.id }}">{{ recipe.title }}</a> 
            - Avg Rating: {{ recipe.avg_rating if recipe.avg_rating else 'No ratings' }}
        </li>
        {% endfor %}
    </ul>
</body>
</html>
"""

DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>{{ recipe.title }}</title></head>
<body>
    <h1>{{ recipe.title }}</h1>
    <h3>Ingredients</h3>
    <ul>{% for ing in recipe.ingredients %}\n<li>{{ ing }}</li>\n{% endfor %}</ul>
    <h3>Instructions</h3>
    <p>{{ recipe.instructions }}</p>
    <h3>Average Rating: {{ recipe.avg_rating if recipe.avg_rating else 'N/A' }}</h3>
    <h3>Comments</h3>
    <ul>{% for c in recipe.comments %}\n<li>{{ c }}</li>\n{% endfor %}</ul>
    <hr>
    <a href="/recipes">Back to Overview</a>
</body>
</html>
"""

@app.route('/recipes', methods=['GET'])
def get_recipes_overview():
    conn = get_db_connection()
    # Get recipes and their average rating
    query = '''
        SELECT r.id, r.title, AVG(rt.rating) as avg_rating 
        FROM recipes r 
        LEFT JOIN ratings rt ON r.id = rt.recipe_id 
        GROUP BY r.id 
        ORDER BY avg_rating DESC, r.id DESC
    '''
    recipes = conn.execute(query).fetchall()
    conn.close()
    return render_template_string(OVERVIEW_TEMPLATE, recipes=recipes)

@app.route('/recipes/upload', methods=['POST'])
def upload_recipe():
    data = request.get_json()
    if not data or not all(k in data for k in ('title', 'ingredients', 'instructions')):
        return jsonify({"error": "Invalid input"}), 400
    
    title = data['title']
    ingredients = json.dumps(data['ingredients'])
    instructions = data['instructions']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)', 
                   (title, ingredients, instructions))
    recipe_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        "id": str(recipe_id),
        "title": title,
        "ingredients": data['ingredients'],
        "instructions": instructions,
        "comments": [],
        "avgRating": None
    }), 201

@app.route('/recipes/<recipeId>', methods=['GET'])
def get_recipe(recipeId):
    try:
        recipe_id = int(recipeId)
    except ValueError:
        return jsonify({"error": "Invalid ID"}), 400

    conn = get_db_connection()
    recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,)).fetchone()
    
    if recipe is None:
        conn.close()
        return jsonify({"error": "Recipe not found"}), 404
    
    comments = conn.execute('SELECT comment FROM comments WHERE recipe_id = ?', (recipe_id,)).fetchall()
    ratings = conn.execute('SELECT rating FROM ratings WHERE recipe_id = ?', (recipe_id,)).fetchall()
    conn.close()
    
    avg_rating = sum([r['rating'] for r in ratings]) / len(ratings) if ratings else None
    
    recipe_data = {
        "title": recipe['title'],
        "ingredients": json.loads(recipe['ingredients']),
        "instructions": recipe['instructions'],
        "comments": [c['comment'] for c in comments],
        "avg_rating": round(avg_rating, 2) if avg_rating else None
    }
    
    return render_template_string(DETAIL_TEMPLATE, recipe=recipe_data)

@app.route('/recipes/<recipeId>/comments', methods=['POST'])
def add_comment(recipeId):
    try:
        recipe_id = int(recipeId)
    except ValueError:
        return jsonify({"error": "Invalid ID"}), 400
        
    data = request.get_json()
    if not data or 'comment' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    conn = get_db_connection()
    recipe = conn.execute('SELECT id FROM recipes WHERE id = ?', (recipe_id,)).fetchone()
    if recipe is None:
        conn.close()
        return jsonify({"error": "Recipe not found"}), 404
    
    conn.execute('INSERT INTO comments (recipe_id, comment) VALUES (?, ?)', (recipe_id, data['comment']))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Comment added successfully"}), 201

@app.route('/recipes/<recipeId>/ratings', methods=['POST'])
def add_rating(recipeId):
    try:
        recipe_id = int(recipeId)
    except ValueError:
        return jsonify({"error": "Invalid ID"}), 400
        
    data = request.get_json()
    if not data or 'rating' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    rating = data['rating']
    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400
    
    conn = get_db_connection()
    recipe = conn.execute('SELECT id FROM recipes WHERE id = ?', (recipe_id,)).fetchone()
    if recipe is None:
        conn.close()
        return jsonify({"error": "Recipe not found"}), 404
    
    conn.execute('INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)', (recipe_id, rating))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Rating added successfully"}), 201

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)