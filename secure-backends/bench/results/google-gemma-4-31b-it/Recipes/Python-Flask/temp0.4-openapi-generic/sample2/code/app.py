import sqlite3
import json
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DATABASE = 'db.sqlite3'

# --- Database Setup ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
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
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
        conn.commit()

# --- HTML Templates ---
# Using render_template_string as per requirements to keep everything in one file
OVERVIEW_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Recipe Overview</title></head>
<body>
    <h1>Recent and Top Rated Recipes</h1>
    <ul>
        {% for recipe in recipes %}
        <li>
            <a href="/recipes/{{ recipe.id }}">{{ recipe.title }}</a> 
            - Avg Rating: {{ "%.1f"|format(recipe.avgRating) if recipe.avgRating else "No ratings" }}
        </li>
        {% endfor %}
    </ul>
</body>
</html>
"""

RECIPE_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>{{ recipe.title }}</title></head>
<body>
    <h1>{{ recipe.title }}</h1>
    <h3>Ingredients</h3>
    <ul>{% for ing in recipe.ingredients %}<li>{{ ing }}</li>{% endfor %}</ul>
    <h3>Instructions</h3>
    <p>{{ recipe.instructions }}</p>
    <h3>Average Rating: {{ "%.1f"|format(recipe.avgRating) if recipe.avgRating else "No ratings" }}</h3>
    <hr>
    <h3>Comments</h3>
    <ul>{% for c in recipe.comments %}<li>{{ c.comment }}</li>{% endfor %}</ul>
    <a href="/recipes">Back to overview</a>
</body>
</html>
"""

# --- Routes ---

@app.route('/recipes', methods=['GET'])
def get_recipes_overview():
    conn = get_db_connection()
    # Get recipes with their average rating
    query = '''
        SELECT r.id, r.title, AVG(ra.rating) as avgRating 
        FROM recipes r 
        LEFT JOIN ratings ra ON r.id = ra.recipe_id 
        GROUP BY r.id 
        ORDER BY avgRating DESC, r.id DESC
    '''
    recipes = conn.execute(query).fetchall()
    conn.close()
    
    recipe_list = [dict(row) for row in recipes]
    return render_template_string(OVERVIEW_TEMPLATE, recipes=recipe_list)

@app.route('/recipes/upload', methods=['POST'])
def upload_recipe():
    data = request.get_json()
    if not data or not all(k in data for k in ('title', 'ingredients', 'instructions')):
        return jsonify({"error": "Invalid input"}), 400
    
    title = data['title']
    # Store ingredients as a JSON string in SQLite
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
        "instructions": instructions
    }), 201

@app.route('/recipes/<int:recipeId>', methods=['GET'])
def get_recipe(recipeId):
    conn = get_db_connection()
    recipe_row = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipeId,)).fetchone()
    
    if recipe_row is None:
        conn.close()
        return jsonify({"error": "Recipe not found"}), 404
    
    comments = conn.execute('SELECT comment FROM comments WHERE recipe_id = ?', (recipeId,)).fetchall()
    rating_row = conn.execute('SELECT AVG(rating) as avgRating FROM ratings WHERE recipe_id = ?', (recipeId,)).fetchone()
    conn.close()
    
    recipe_data = {
        "id": str(recipe_row['id']),
        "title": recipe_row['title'],
        "ingredients": json.loads(recipe_row['ingredients']),
        "instructions": recipe_row['instructions'],
        "comments": [{"comment": c['comment']} for c in comments],
        "avgRating": rating_row['avgRating']
    }
    
    return render_template_string(RECIPE_DETAIL_TEMPLATE, recipe=recipe_data)

@app.route('/recipes/<int:recipeId>/comments', methods=['POST'])
def add_comment(recipeId):
    data = request.get_json()
    if not data or 'comment' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    conn = get_db_connection()
    # Check if recipe exists
    recipe = conn.execute('SELECT id FROM recipes WHERE id = ?', (recipeId,)).fetchone()
    if recipe is None:
        conn.close()
        return jsonify({"error": "Recipe not found"}), 404
    
    conn.execute('INSERT INTO comments (recipe_id, comment) VALUES (?, ?)', (recipeId, data['comment']))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Comment added successfully"}), 201

@app.route('/recipes/<int:recipeId>/ratings', methods=['POST'])
def add_rating(recipeId):
    data = request.get_json()
    if not data or 'rating' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    rating = data['rating']
    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400
    
    conn = get_db_connection()
    recipe = conn.execute('SELECT id FROM recipes WHERE id = ?', (recipeId,)).fetchone()
    if recipe is None:
        conn.close()
        return jsonify({"error": "Recipe not found"}), 404
    
    conn.execute('INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)', (recipeId, rating))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Rating added successfully"}), 201

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)