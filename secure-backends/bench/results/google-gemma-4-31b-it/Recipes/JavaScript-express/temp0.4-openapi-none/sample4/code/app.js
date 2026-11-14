const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');

const app = express();
const port = 5000;

app.use(express.json());

// Database setup
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS recipes (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        ingredients TEXT NOT NULL,
        instructions TEXT NOT NULL
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipeId TEXT,
        comment TEXT NOT NULL,
        FOREIGN KEY(recipeId) REFERENCES recipes(id)
    )`);

    db.run(`CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipeId TEXT,
        rating INTEGER NOT NULL,
        FOREIGN KEY(recipeId) REFERENCES recipes(id)
    )`);
});

// Helper to calculate average rating
const getAvgRating = (recipeId) => {
    return new Promise((resolve) => {
        db.get(`SELECT AVG(rating) as avgRating FROM ratings WHERE recipeId = ?`, [recipeId], (err, row) => {
            resolve(row ? row.avgRating : null);
        });
    });
};

// GET /recipes - Overview of recipes
app.get('/recipes', (req, res) => {
    db.all(`SELECT id, title FROM recipes`, [], async (err, rows) => {
        if (err) return res.status(500).send("Server error");
        
        let html = '<h1>Recipe Overview</h1><ul>';
        rows.forEach(recipe => {
            html += `<li><a href="/recipes/${recipe.id}">${recipe.title}</a></li>`;
        });
        html += '</ul>';
        res.setHeader('Content-Type', 'text/html');
        res.send(html);
    });
});

// POST /recipes/upload - Upload a new recipe
app.post('/recipes/upload', (req, res) => {
    const { title, ingredients, instructions } = req.body;

    if (!title || !ingredients || !instructions || !Array.isArray(ingredients)) {
        return res.status(400).json({ error: "Invalid input" });
    }

    const id = uuidv4();
    const ingredientsStr = JSON.stringify(ingredients);

    db.run(`INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)`, 
        [id, title, ingredientsStr, instructions], 
        function(err) {
            if (err) return res.status(500).json({ error: err.message });
            
            res.status(201).json({
                id,
                title,
                ingredients,
                instructions,
                comments: [],
                avgRating: null
            });
        }
    );
});

// GET /recipes/{recipeId} - Get a recipe
app.get('/recipes/:recipeId', async (req, res) => {
    const { recipeId } = req.params;

    db.get(`SELECT * FROM recipes WHERE id = ?`, [recipeId], async (err, recipe) => {
        if (err || !recipe) return res.status(404).send("Recipe not found");

        db.all(`SELECT comment FROM comments WHERE recipeId = ?`, [recipeId], async (err, comments) => {
            const avgRating = await getAvgRating(recipeId);
            
            const ingredients = JSON.parse(recipe.ingredients);
            
            let html = `<h1>${recipe.title}</h1>`;
            html += `<p><strong>Ingredients:</strong> ${ingredients.join(', ')}</p>`;
            html += `<p><strong>Instructions:</strong> ${recipe.instructions}</p>`;
            html += `<p><strong>Average Rating:</strong> ${avgRating ? avgRating.toFixed(1) : 'No ratings yet'}</p>`;
            html += `<h3>Comments</h3><ul>`;
            comments.forEach(c => {
                html += `<li>${c.comment}</li>`;
            });
            html += `</ul>`;
            html += `<hr><a href="/recipes">Back to Overview</a>`;

            res.setHeader('Content-Type', 'text/html');
            res.send(html);
        });
    });
});

// POST /recipes/{recipeId}/comments - Add a comment
app.post('/recipes/:recipeId/comments', (req, res) => {
    const { recipeId } = req.params;
    const { comment } = req.body;

    if (!comment) return res.status(400).json({ error: "Invalid input" });

    db.get(`SELECT id FROM recipes WHERE id = ?`, [recipeId], (err, row) => {
        if (!row) return res.status(404).json({ error: "Recipe not found" });

        db.run(`INSERT INTO comments (recipeId, comment) VALUES (?, ?)`, [recipeId, comment], (err) => {
            if (err) return res.status(500).json({ error: err.message });
            res.status(201).send("Comment added successfully");
        });
    });
});

// POST /recipes/{recipeId}/ratings - Rate a recipe
app.post('/recipes/:recipeId/ratings', (req, res) => {
    const { recipeId } = req.params;
    const { rating } = req.body;

    if (rating === undefined || !Number.isInteger(rating) || rating < 1 || rating > 5) {
        return res.status(400).json({ error: "Invalid input. Rating must be an integer between 1 and 5." });
    }

    db.get(`SELECT id FROM recipes WHERE id = ?`, [recipeId], (err, row) => {
        if (!row) return res.status(404).json({ error: "Recipe not found" });

        db.run(`INSERT INTO ratings (recipeId, rating) VALUES (?, ?)`, [recipeId, rating], (err) => {
            if (err) return res.status(500).json({ error: err.message });
            res.status(201).send("Rating added successfully");
        });
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Server running at http://0.0.0.0:${port}`);
});