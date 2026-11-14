import sqlite3
import json
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_NAME = "db.sqlite3"

# Security: Bound request size to prevent resource exhaustion (DoS)
# Limit request body to 1MB
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
# Security: Jinja2 automatically escapes variables passed to render_template_string, 
# preventing XSS. We use a static string for the template itself to avoid Template Injection.
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Recipe Overview</title></head>
<body>
    <h1>Recent & Top Rated Recipes</h1>
    <ul>
    {% for recipe in recipes %}
        <li><a href="/recipes/{{ recipe.id }}">{{ recipe.title }}</a> (Rating: {{ recipe.avg_rating or 'No ratings' }})</li>
    {% endfor %}
    </ul>
</body>
</html>
'''

RECIPE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{{ recipe.title }}</title></head>
<body>
    <h1>{{ recipe.title }}</h1>
    <h3>Ingredients</h3>
    <ul>{% for ing in recipe.ingredients %}<li>{{ ing }}</li>{% endfor %}</ul>
    <h3>Instructions</h3>
    <p>{{ recipe.instructions }}</p>
    <h3>Average Rating: {{ recipe.avg_rating or 'N/A' }}</h3>
    <hr>
    <h3>Comments</h3>
    <ul>{% for c in recipe.comments %}<li>{{ c.comment }}</li>{% endfor %}</ul>
    <a href="/recipes">Back to Overview</a>
</body>
</html>
'''

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
        return render_template_string(INDEX_TEMPLATE, recipes=recipes)
    except Exception:
        # Security: Generic 500 error to avoid leaking internal stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/upload', methods=['POST'])
def upload_recipe():
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400
            
        if not all(k in data for k in ('title', 'ingredients', 'instructions')):
            return jsonify({"error": "Invalid input"}), 400
        
        # Validate types to prevent unexpected behavior
        if not isinstance(data['title'], str) or not isinstance(data['instructions'], str) or not isinstance(data['ingredients'], list):
            return jsonify({"error": "Invalid input types"}), 400

        title = data['title']
        # Use json.dumps for safe storage of the list
        ingredients = json.dumps(data['ingredients'])
        instructions = data['instructions']
        
        conn = get_db_connection()
        cur = conn.cursor()
        # Security: Use parameterized query to prevent SQL Injection
        cur.execute('INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)', 
                    (title, ingredients, instructions))
        recipe_id = cur.lastrowid
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
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/<int:recipeId>', methods=['GET'])
def get_recipe(recipeId):
    try:
        conn = get_db_connection()
        # Security: Parameterized query to prevent SQL Injection
        recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipeId,)).fetchone()
        
        if recipe is None:
            conn.close()
            return jsonify({"error": "Recipe not found"}), 404
        
        comments = conn.execute('SELECT comment FROM comments WHERE recipe_id = ?', (recipeId,)).fetchall()
        rating_row = conn.execute('SELECT AVG(rating) as avg_rating FROM ratings WHERE recipe_id = ?', (recipeId,)).fetchone()
        conn.close()
        
        recipe_data = {
            "title": recipe['title'],
            "ingredients": json.loads(recipe['ingredients']),
            "instructions": recipe['instructions'],
            "comments": [dict(row) for row in comments],
            "avg_rating": rating_row['avg_rating']
        }
        
        # Security: render_template_string handles HTML escaping of recipe_data
        return render_template_string(RECIPE_TEMPLATE, recipe=recipe_data)
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/<int:recipeId>/comments', methods=['POST'])
def add_comment(recipeId):
    try:
        data = request.get_json(silent=True)
        if data is None or 'comment' not in data or not isinstance(data['comment'], str):
            return jsonify({"error": "Invalid input"}), 400
        
        conn = get_db_connection()
        recipe = conn.execute('SELECT id FROM recipes WHERE id = ?', (recipeId,)).fetchone()
        if recipe is None:
            conn.close()
            return jsonify({"error": "Recipe not found"}), 404
        
        # Security: Parameterized query to prevent SQL Injection
        conn.execute('INSERT INTO comments (recipe_id, comment) VALUES (?, ?)', (recipeId, data['comment']))
        conn.commit()
        conn.close()
        return jsonify({"status": "Comment added successfully"}), 201
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/recipes/<int:recipeId>/ratings', methods=['POST'])
def add_rating(recipeId):
    try:
        data = request.get_json(silent=True)
        if data is None or 'rating' not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        rating = data['rating']
        # Security: Strict type and range validation
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            return jsonify({"error": "Invalid input"}), 400
        
        conn = get_db_connection()
        recipe = conn.execute('SELECT id FROM recipes WHERE id = ?', (recipeId,)).fetchone()
        if recipe is None:
            conn.close()
            return jsonify({"error": "Recipe not found"}), 404
        
        # Security: Parameterized query to prevent SQL Injection
        conn.execute('INSERT INTO ratings (recipe_id, rating) VALUES (?, ?)', (recipeId, rating))
        conn.commit()
        conn.close()
        return jsonify({"status": "Rating added successfully"}), 201
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    # Security: Running on 0.0.0.0 as requested, but in production, a WSGI server (gunicorn) is recommended.
    app.run(host='0.0.0.0', port=5000)