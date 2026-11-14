import sqlite3
import json
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_NAME = "db.sqlite3"

# --- Database Setup ---
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Recipes table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL
            )
        ''')
        # Comments table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
        # Ratings table
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
OVERVIEW_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Recipe Overview</title></head>
<body>
    <h1>Recent & Top Rated Recipes</h1>
    <ul>
        {% for recipe in recipes %}
        <li>
            <a href="/recipes/{{ recipe.id }}">{{ recipe.title }}</a> 
            (Avg Rating: {{ recipe.avg_rating if recipe.avg_rating else 'N/A' }})
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
    <ul>
        {% for ing in ingredients %}
        <li>{{ ing }}</li>
        {% endfor %}
    </ul>
    <h3>Instructions</h3>
    <p>{{ recipe.instructions }}</p>
    <h3>Average Rating: {{ recipe.avg_rating if recipe.avg_rating else 'No ratings yet' }}</h3>
    
    <h3>Comments</h3>
    <ul>
        {% for c in comments %}
        <li>{{ c }}</li>
        {% endfor %}
    </ul>
    <hr>
    <a href="/recipes">Back to Overview</a>
</body>
</html>
"""

# --- API Endpoints ---

@app.route('/recipes', methods=['GET'])
def get_recipes_overview():
    try:
        with get_db() as conn:
            # Get recipes and their average ratings
            query = '''
                SELECT r.id, r.title, AVG(ra.rating) as avg_rating 
                FROM recipes r 
                LEFT JOIN ratings ra ON r.id = ra.recipe_id 
                GROUP BY r.id 
                ORDER BY avg_rating DESC, r.id DESC
            '''
            recipes = conn.execute(query).fetchall()
            return render_template_string(OVERVIEW_TEMPLATE, recipes=recipes)
    except Exception as e:
        return "Server Error", 500

@app.route('/recipes/upload', methods=['POST'])
def upload_recipe():
    data = request.get_json()
    if not data or not all(k in data for k in ('title', 'ingredients', 'instructions')):
        return jsonify({"error": "Invalid input"}), 400
    
    if not isinstance(data['ingredients'], list):
        return jsonify({"error": "Ingredients must be a list"}), 400

    try:
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)",
                (data['title'], json.dumps(data['ingredients']), data['instructions'])
            )
            recipe_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                "id": str(recipe_id),
                "title": data['title'],
                "ingredients": data['ingredients'],
                "instructions": data['instructions'],
                "comments": [],
                "avgRating": None
            }), 201
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/<int:recipeId>', methods=['GET'])
def get_recipe(recipeId):
    with get_db() as conn:
        recipe = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipeId,)).fetchone()
        if not recipe:
            return "Recipe not found", 404
        
        comments = conn.execute("SELECT comment FROM comments WHERE recipe_id = ?", (recipeId,)).fetchall()
        rating = conn.execute("SELECT AVG(rating) FROM ratings WHERE recipe_id = ?", (recipeId,)).fetchone()
        
        ingredients = json.loads(recipe['ingredients'])
        comment_list = [row['comment'] for row in comments]
        avg_rating = rating[0] if rating[0] is not None else None
        
        return render_template_string(
            RECIPE_DETAIL_TEMPLATE, 
            recipe={"title": recipe['title'], "instructions": recipe['instructions'], "avg_rating": avg_rating},
            ingredients=ingredients,
            comments=comment_list
        )

@app.route('/recipes/<int:recipeId>/comments', methods=['POST'])
def add_comment(recipeId):
    data = request.get_json()
    if not data or 'comment' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    with get_db() as conn:
        # Check if recipe exists
        recipe = conn.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,)).fetchone()
        if not recipe:
            return jsonify({"error": "Recipe not found"}), 404
        
        conn.execute("INSERT INTO comments (recipe_id, comment) VALUES (?, ?)", (recipeId, data['comment']))
        conn.commit()
        return "", 201

@app.route('/recipes/<int:recipeId>/ratings', methods=['POST'])
def add_rating(recipeId):
    data = request.get_json()
    if not data or 'rating' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    rating = data['rating']
    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400
    
    with get_db() as conn:
        recipe = conn.execute("SELECT id FROM recipes WHERE id = ?", (recipeId,)).fetchone()
        if not recipe:
            return jsonify({"error": "Recipe not found"}), 404
        
        conn.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)", (recipeId, rating))
        conn.commit()
        return "", 201

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)