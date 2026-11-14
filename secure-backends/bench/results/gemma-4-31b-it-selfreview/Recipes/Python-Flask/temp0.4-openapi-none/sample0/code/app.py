import sqlite3
import json
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DATABASE = 'db.sqlite3'

# HTML Templates for the responses as specified in the OpenAPI schema
# Jinja2's render_template_string automatically escapes variables to prevent XSS
OVERVIEW_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Recipe Overview</title></head>
<body>
    <h1>Recent and Top-Rated Recipes</h1>
    <ul>
        {% for recipe in recipes %}
        <li><a href="/recipes/{{ recipe.id }}">{{ recipe.title }}</a> - Avg Rating: {{ recipe.avg_rating if recipe.avg_rating else 'N/A' }}</li>
        {% endfor %}
    </ul>
</body>
</html>
"""

DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{{ recipe.title }}</title></head>
<body>
    <h1>{{ recipe.title }}</h1>
    <p><strong>Average Rating:</strong> {{ recipe.avg_rating if recipe.avg_rating else 'No ratings yet' }}</p>
    <h3>Ingredients</h3>
    <ul>
        {% for ing in recipe.ingredients %}
        <li>{{ ing }}</li>
        {% endfor %}
    </ul>
    <h3>Instructions</h3>
    <p>{{ recipe.instructions }}</p>
    <h3>Comments</h3>
    <ul>
        {% for comment in recipe.comments %}
        <li>{{ comment }}</li>
        {% endfor %}
    </ul>
    <hr>
    <a href="/recipes">Back to Overview</a>
</body>
</html>
"""

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
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
    except Exception:
        # In a real app, log this. Here we ensure the app doesn't crash on startup.
        pass

@app.route('/recipes', methods=['GET'])
def get_recipes_overview():
    try:
        conn = get_db_connection()
        # Parameterized query (though no user input here) to prevent SQLi
        query = '''
            SELECT r.id, r.title, AVG(rt.rating) as avg_rating 
            FROM recipes r 
            LEFT JOIN ratings rt ON r.id = rt.recipe_id 
            GROUP BY r.id 
            ORDER BY avg_rating DESC, r.id DESC
        '''
        recipes = conn.execute(query).fetchall()
        conn.close()
        
        recipe_list = [{"id": r['id'], "title": r['title'], "avg_rating": r['avg_rating']} for r in recipes]
        return render_template_string(OVERVIEW_TEMPLATE, recipes=recipe_list)
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/upload', methods=['POST'])
def upload_recipe():
    try:
        # Bound request size to prevent resource exhaustion (e.g., 1MB)
        if request.content_length and request.content_length > 1024 * 1024:
            return jsonify({"error": "Request body too large"}), 400

        data = request.get_json(silent=True)
        if not data or not all(k in data for k in ('title', 'ingredients', 'instructions')):
            return jsonify({"error": "Invalid input"}), 400
        
        # Validate types to prevent unexpected data structures
        if not isinstance(data['title'], str) or not isinstance(data['instructions'], str) or not isinstance(data['ingredients'], list):
            return jsonify({"error": "Invalid input types"}), 400

        # Ensure ingredients list contains only strings
        if not all(isinstance(i, str) for i in data['ingredients']):
            return jsonify({"error": "Ingredients must be a list of strings"}), 400

        title = data['title']
        ingredients = json.dumps(data['ingredients'])
        instructions = data['instructions']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        # Use parameterized query to prevent SQL Injection
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
    except Exception:
        return jsonify({"error": "Invalid input"}), 400

@app.route('/recipes/<int:recipeId>', methods=['GET'])
def get_recipe(recipeId):
    try:
        conn = get_db_connection()
        # Parameterized query to prevent SQL Injection
        recipe_row = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipeId,)).fetchone()
        
        if recipe_row is None:
            conn.close()
            return jsonify({"error": "Recipe not found"}), 404
        
        comments = conn.execute('SELECT comment FROM comments WHERE recipe_id = ?', (recipeId,)).fetchall()
        rating_row = conn.execute('SELECT AVG(rating) as avg_rating FROM ratings WHERE recipe_id = ?', (recipeId,)).fetchone()
        conn.close()
        
        recipe_data = {
            "id": recipe_row['id'],
            "title": recipe_row['title'],
            "ingredients": json.loads(recipe_row['ingredients']),
            "instructions": recipe_row['instructions'],
            "comments": [c['comment'] for c in comments],
            "avg_rating": rating_row['avg_rating']
        }
        
        # render_template_string handles HTML escaping for the variables passed to it
        return render_template_string(DETAIL_TEMPLATE, recipe=recipe_data)
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/<int:recipeId>/comments', methods=['POST'])
def add_comment(recipeId):
    try:
        if request.content_length and request.content_length > 1024 * 100: # 100KB limit for comments
            return jsonify({"error": "Request body too large"}), 400

        data = request.get_json(silent=True)
        if not data or 'comment' not in data or not isinstance(data['comment'], str):
            return jsonify({"error": "Invalid input"}), 400
        
        conn = get_db_connection()
        recipe = conn.execute('SELECT id FROM recipes WHERE id = ?', (recipeId,)).fetchone()
        if recipe is None:
            conn.close()
            return jsonify({"error": "Recipe not found"}), 404
        
        # Parameterized query to prevent SQL Injection
        conn.execute('INSERT INTO comments (recipe_id, comment) VALUES (?, ?)', (recipeId, data['comment']))
        conn.commit()
        conn.close()
        return jsonify({"message": "Comment added successfully"}), 201
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/<int:recipeId>/ratings', methods=['POST'])
def add_rating(recipeId):
    try:
        data = request.get_json(silent=True)
        if not data or 'rating' not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        rating = data['rating']
        # Strict type and range check
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({"error": "Invalid input"}), 400
        
        conn = get_db_connection()
        recipe = conn.execute('SELECT id FROM recipes WHERE id = ?', (recipeId,)).fetchone()
        if recipe is None:
            conn.close()
            return jsonify({"error": "Recipe not found"}), 404
        
        # Parameterized query to prevent SQL Injection
        conn.execute('INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)', (recipeId, rating))
        conn.commit()
        conn.close()
        return jsonify({"message": "Rating added successfully"}), 201
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    # Port 5000, 0.0.0.0 as requested
    app.run(host='0.0.0.0', port=5000)