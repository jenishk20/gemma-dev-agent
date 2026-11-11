const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(express.json());

const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
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
    return new Promise((resolve, reject) => {
        db.get(`SELECT AVG(rating) as avgRating FROM ratings WHERE recipeId = ?`, [recipeId], (err, row) => {
            if (err) reject(err);
            else resolve(row ? row.avgRating : null);
        });
    });
};

// Helper to get comments
const getComments = (recipeId) => {
    return new Promise((resolve, reject) => {
        db.all(`SELECT comment FROM comments WHERE recipeId = ?`, [recipeId], (err, rows) => {
            if (err) reject(err);
            else resolve(rows);
        });
    });
};

// GET /recipes - Overview of recipes
app.get('/recipes', async (req, res) => {
    db.all(`SELECT id, title FROM recipes`, async (err, rows) => {
        if (err) return res.status(500).send('Server error');
        
        let html = '<h1>Recipe Overview</h1><ul>';
        for (const row of rows) {
            html += `<li><a href="/recipes/${row.id}">${row.title}</a></li>`;
        }
        html += '</ul>';
        res.setHeader('Content-Type', 'text/html');
        res.status(200).send(html);
    });
});

// POST /recipes/upload - Upload a new recipe
app.post('/recipes/upload', (req, res) => {
    const { title, ingredients, instructions } = req.body;
    if (!title || !ingredients || !instructions) {
        return res.status(400).json({ error: 'Invalid input' });
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

// GET /recipes/{recipeId} - Get a specific recipe
app.get('/recipes/:recipeId', async (req, res) => {
    const { recipeId } = req.params;
    db.get(`SELECT * FROM recipes WHERE id = ?`, [recipeId], async (err, row) => {
        if (err || !row) return res.status(404).send('Recipe not found');

        try {
            const avgRating = await getAvgRating(recipeId);
            const comments = await getComments(recipeId);
            
            let html = `<h1>${row.title}</h1>`;
            html += `<h3>Ingredients</h3><ul>`;
            JSON.parse(row.ingredients).forEach(ing => {
                html += `<li>${ing}</li>`;
            });
            html += `</ul><h3>Instructions</h3><p>${row.instructions}</p>`;
            html += `<p><strong>Average Rating:</strong> ${avgRating ? avgRating.toFixed(1) : 'No ratings'}</p>`;
            html += `<h3>Comments</h3><ul>`;
            comments.forEach(c => {
                html += `<li>${c.comment}</li>`;
            });
            html += `</ul><br><a href="/recipes">Back to list</a>`;
            
            res.setHeader('Content-Type', 'text/html');
            res.status(200).send(html);
        } catch (e) {
            res.status(500).send('Server error');
        }
    });
});

// POST /recipes/{recipeId}/comments - Add a comment
app.post('/recipes/:recipeId/comments', (req, res) => {
    const { recipeId } = req.params;
    const { comment } = req.body;

    if (!comment) return res.status(400).json({ error: 'Invalid input' });

    db.get(`SELECT id FROM recipes WHERE id = ?`, [recipeId], (err, row) => {
        if (!row) return res.status(404).json({ error: 'Recipe not found' });
        
        db.run(`INSERT INTO comments (recipeId, comment) VALUES (?, ?)`, [recipeId, comment], (err) => {
            if (err) return res.status(500).json({ error: err.message });
            res.status(201).send('Comment added successfully');
        });
    });
});

// POST /recipes/{recipeId}/ratings - Rate a recipe
app.post('/recipes/:recipeId/ratings', (req, res) => {
    const { recipeId } = req.params;
    const { rating } = req.body;

    if (rating === undefined || !Number.isInteger(rating) || rating < 1 || rating > 5) {
        return res.status(400).json({ error: 'Invalid input' });
    }

    db.get(`SELECT id FROM recipes WHERE id = ?`, [recipeId], (err, row) => {
        if (!row) return res.status(404).json({ error: 'Recipe not found' });

        db.run(`INSERT INTO ratings (recipeId, rating) VALUES (?, ?)`, [recipeId, rating], (err) => {
            if (err) return res.status(500).json({ error: err.message });
            res.status(201).send('Rating added successfully');
        });
    });
});

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});