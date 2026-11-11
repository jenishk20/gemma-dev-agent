import sqlite3
import json
from flask import Flask, request, jsonify, render_template_string, escape

app = Flask(__name__)
DB_NAME = 'db.sqlite3'

# Resource exhaustion: Limit request body size to 1MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

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

# HTML Templates
# Using Jinja2's auto-escaping (default in render_template_string) 
# to prevent XSS when rendering user-provided content.
OVERVIEW_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Recipe Overview</title></head>
<body>
    <h1>Recent and Top Rated Recipes</h1>
    <ul>
    {% for recipe in recipes %}
        <li>
            <a href="/recipes/{{ recipe.id }}">{{ recipe.title }}</a> 
            (Avg Rating: {{ "%.1f"|format(recipe.avg_rating) if recipe.avg_rating else "No ratings" }})
        </li>
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
    <h3>Ingredients</h3>
    <ul>{% for ing in recipe.ingredients %}<li>{{ ing }}</li>{% endfor %}</ul>
    <h3>Instructions</h3>
    <p>{{ recipe.instructions }}</p>
    <h3>Average Rating: {{ "%.1f"|format(recipe.avg_rating) if recipe.avg_rating else "N/A" }}</h3>
    <h3>Comments</h3>
    <ul>{% for c in recipe.comments %}<li>{{ c }}</li>{% endfor %}</ul>
    <hr>
    <a href="/recipes">Back to Overview</a>
</body>
</html>
"""

@app.route('/recipes', methods=['GET'])
def get_recipes_overview():
    try:
        conn = get_db_connection()
        # Parameterized query (though no user input here) to prevent SQLi
        query = '''
            SELECT r.id, r.title, AVG(ra.rating) as avg_rating 
            FROM recipes r 
            LEFT JOIN ratings ra ON r.id = ra.recipe_id 
            GROUP BY r.id 
            ORDER BY avg_rating DESC, r.id DESC
        '''
        recipes = conn.execute(query).fetchall()
        conn.close()
        return render_template_string(OVERVIEW_TEMPLATE, recipes=recipes)
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/upload', methods=['POST'])
def upload_recipe():
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400
        
        if not all(k in data for k in ('title', 'ingredients', 'instructions')):
            return jsonify({"error": "Invalid input"}), 400
        
        title = data['title']
        if not isinstance(title, str):
            return jsonify({"error": "Invalid input"}), 400
            
        ingredients = data['ingredients']
        if not isinstance(ingredients, list) or not all(isinstance(i, str) for i in ingredients):
            return jsonify({"error": "Invalid input"}), 400
            
        instructions = data['instructions']
        if not isinstance(instructions, str):
            return jsonify({"error": "Invalid input"}), 400

        # Store list as JSON string safely
        ingredients_json = json.dumps(ingredients)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        # Parameterized query to prevent SQL Injection
        cursor.execute('INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)', 
                       (title, ingredients_json, instructions))
        recipe_id = cursor.lastrowid
        conn.commit()
        
        recipe = cursor.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,)).fetchone()
        conn.close()
        
        return jsonify({
            "id": str(recipe['id']),
            "title": recipe['title'],
            "ingredients": json.loads(recipe['ingredients']),
            "instructions": recipe['instructions'],
            "comments": [],
            "avgRating": None
        }), 201
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/<int:recipeId>', methods=['GET'])
def get_recipe(recipeId):
    try:
        conn = get_db_connection()
        # Parameterized query to prevent SQL Injection
        recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipeId,)).fetchone()
        
        if recipe is None:
            conn.close()
            return jsonify({"error": "Recipe not found"}), 404
        
        comments = conn.execute('SELECT comment FROM comments WHERE recipe_id = ?', (recipeId,)).fetchall()
        ratings = conn.execute('SELECT rating FROM ratings WHERE recipe_id = ?', (recipeId,)).fetchall()
        conn.close()
        
        avg_rating = sum(r['rating'] for r in ratings) / len(ratings) if ratings else None
        
        recipe_data = {
            "title": recipe['title'],
            "ingredients": json.loads(recipe['ingredients']),
            "instructions": recipe['instructions'],
            "comments": [c['comment'] for c in comments],
            "avg_rating": avg_rating
        }
        
        # render_template_string automatically escapes variables to prevent XSS
        return render_template_string(DETAIL_TEMPLATE, recipe=recipe_data)
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/<int:recipeId>/comments', methods=['POST'])
def add_comment(recipeId):
    try:
        data = request.get_json(silent=True)
        if data is None or 'comment' not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        comment_text = data['comment']
        if not isinstance(comment_text, str):
            return jsonify({"error": "Invalid input"}), 400
        
        conn = get_db_connection()
        recipe = conn.execute('SELECT id FROM recipes WHERE id = ?', (recipeId,)).fetchone()
        if recipe is None:
            conn.close()
            return jsonify({"error": "Recipe not found"}), 404
        
        # Parameterized query to prevent SQL Injection
        conn.execute('INSERT INTO comments (recipe_id, comment) VALUES (?, ?)', (recipeId, comment_text))
        conn.commit()
        conn.close()
        return jsonify({"message": "Comment added successfully"}), 201
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/<int:recipeId>/ratings', methods=['POST'])
def add_rating(recipeId):
    try:
        data = request.get_json(silent=True)
        if data is None or 'rating' not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        rating = data['rating']
        # Strict type and range check
        if not isinstance(rating, int) or not (1 <= rating <= 5):
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
    # Running with threaded=True to handle basic concurrency and avoiding debug=True in production
    app.run(host='0.0.0.0', port=5000, debug=False)