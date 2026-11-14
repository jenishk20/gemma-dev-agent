import sqlite3
import json
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DATABASE = 'db.sqlite3'

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
                rating INTEGER NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id)
            )
        ''')
        conn.commit()

# HTML Templates
OVERVIEW_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Recipe Sharing App</title></head>
<body>
    <h1>Recent & Top Rated Recipes</h1>
    <ul>
        {% for recipe in recipes %}
        <li>
            <a href="/recipes/{{ recipe.id }}">{{ recipe.title }}</a> 
            (Avg Rating: {{ recipe.avg_rating if recipe.avg_rating else 'No ratings' }})
        </li>
        {% endfor %}
    </ul>
</body>
</html>
'''

DETAIL_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>{{ recipe.title }}</title></head>
<body>
    <h1>{{ recipe.title }}</h1>
    <h3>Ingredients</h3>
    <ul>
        {% for ing in recipe.ingredients %}
        <li>{{ ing }}</li>
        {% endfor %}
    </ul>
    <h3>Instructions</h3>
    <p>{{ recipe.instructions }}</p>
    <h3>Average Rating: {{ recipe.avg_rating if recipe.avg_rating else 'N/A' }}</h3>
    <hr>
    <h3>Comments</h3>
    <ul>
        {% for comment in comments %}
        <li>{{ comment }}</li>
        {% endfor %}
    </ul>
    <a href="/recipes">Back to Overview</a>
</body>
</html>
'''

@app.route('/recipes', methods=['GET'])
def get_recipes_overview():
    try:
        conn = get_db_connection()
        # Get recipes and their average ratings
        query = '''
            SELECT r.id, r.title, AVG(ra.rating) as avg_rating 
            FROM recipes r 
            LEFT JOIN ratings ra ON r.id = ra.recipe_id 
            GROUP BY r.id 
            ORDER BY avg_rating DESC, r.id DESC
        '''
        recipes = conn.execute(query).all()
        conn.close()
        return render_template_string(OVERVIEW_TEMPLATE, recipes=recipes)
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/recipes/upload', methods=['POST'])
def upload_recipe():
    data = request.get_json()
    if not data or not all(k in data for k in ('title', 'ingredients', 'instructions')):
        return jsonify({"error": "Invalid input"}), 400
    
    if not isinstance(data['ingredients'], list):
        return jsonify({"error": "Ingredients must be a list"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO recipes (title, ingredients, instructions) VALUES (?, ?, ?)',
            (data['title'], json.dumps(data['ingredients']), data['instructions'])
        )
        recipe_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            "id": str(recipe_id),
            "title": data['title'],
            "ingredients": data['ingredients'],
            "instructions": data['instructions'],
            "comments": [],
            "avgRating": None
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/recipes/<int:recipeId>', methods=['GET'])
def get_recipe(recipeId):
    conn = get_db_connection()
    recipe = conn.execute('SELECT * FROM recipes WHERE id = ?', (recipeId,)).fetchone()
    
    if recipe is None:
        conn.close()
        return jsonify({"error": "Recipe not found"}), 404
    
    comments = conn.execute('SELECT comment FROM comments WHERE recipe_id = ?', (recipeId,)).fetchall()
    rating_row = conn.execute('SELECT AVG(rating) as avg FROM ratings WHERE recipe_id = ?', (recipeId,)).fetchone()
    conn.close()

    recipe_data = {
        "title": recipe['title'],
        "ingredients": json.loads(recipe['ingredients']),
        "instructions": recipe['instructions'],
        "avg_rating": rating_row['avg'] if rating_row['avg'] else 0,
        "id": recipeId
    }
    
    comment_list = [row['comment'] for row in comments]
    
    return render_template_string(DETAIL_TEMPLATE, recipe=recipe_data, comments=comment_list)

@app.route('/recipes/<int:recipeId>/comments', methods=['POST'])
def add_comment(recipeId):
    data = request.get_json()
    if not data or 'comment' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    conn = get_db_connection()
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