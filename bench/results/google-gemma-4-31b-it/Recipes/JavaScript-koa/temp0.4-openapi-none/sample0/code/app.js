const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');

const app = new Koa();
const router = new Router();
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

// Helper to wrap db.all in a promise
const query = (sql, params = []) => {
    return new Promise((resolve, reject) => {
        db.all(sql, params, (err, rows) => {
            if (err) reject(err);
            else resolve(rows);
        });
    });
};

// Helper to wrap db.run in a promise
const run = (sql, params = []) => {
    return new Promise((resolve, reject) => {
        db.run(sql, params, function(err) {
            if (err) reject(err);
            else resolve(this);
        });
    });
};

// GET /recipes - Overview of recipes
router.get('/recipes', async (ctx) => {
    try {
        const recipes = await query('SELECT id, title FROM recipes');
        let html = '<h1>Recipe Overview</h1><ul>';
        recipes.forEach(r => {
            html += `<li><a href="/recipes/${r.id}">${r.title}</a></li>`;
        });
        html += '</ul>';
        ctx.type = 'text/html';
        ctx.body = html;
    } catch (e) {
        ctx.status = 500;
        ctx.body = 'Internal Server Error';
    }
});

// POST /recipes/upload - Upload a new recipe
router.post('/recipes/upload', async (ctx) => {
    const { title, ingredients, instructions } = ctx.request.body;
    if (!title || !ingredients || !instructions) {
        ctx.status = 400;
        ctx.body = { error: 'Invalid input' };
        return;
    }

    const id = uuidv4();
    const ingredientsStr = JSON.stringify(ingredients);
    
    try {
        await run('INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)', [id, title, ingredientsStr, instructions]);
        ctx.status = 201;
        ctx.body = { id, title, ingredients, instructions };
    } catch (e) {
        ctx.status = 500;
        ctx.body = { error: 'Database error' };
    }
});

// GET /recipes/{recipeId} - Get a specific recipe
router.get('/recipes/:recipeId', async (ctx) => {
    const { recipeId } = ctx.params;
    try {
        const recipeRows = await query('SELECT * FROM recipes WHERE id = ?', [recipeId]);
        if (recipeRows.length === 0) {
            ctx.status = 404;
            ctx.body = 'Recipe not found';
            return;
        }

        const recipe = recipeRows[0];
        const comments = await query('SELECT comment FROM comments WHERE recipeId = ?', [recipeId]);
        const ratings = await query('SELECT rating FROM ratings WHERE recipeId = ?', [recipeId]);

        const avgRating = ratings.length > 0 
            ? ratings.reduce((acc, curr) => acc + curr.rating, 0) / ratings.length 
            : null;

        const ingredients = JSON.parse(recipe.ingredients);

        let html = `<h1>${recipe.title}</h1>`;
        html += `<p><strong>Ingredients:</strong> ${ingredients.join(', ')}</p>`;
        html += `<p><strong>Instructions:</strong> ${recipe.instructions}</p>`;
        html += `<p><strong>Average Rating:</strong> ${avgRating !== null ? avgRating.toFixed(1) : 'No ratings'}</p>`;
        html += `<h3>Comments</h3><ul>`;
        comments.forEach(c => { html += `<li>${c.comment}</li>`; });
        html += `</ul>`;
        html += `<hr><a href="/recipes">Back to overview</a>`;

        ctx.type = 'text/html';
        ctx.body = html;
    } catch (e) {
        ctx.status = 500;
        ctx.body = 'Internal Server Error';
    }
});

// POST /recipes/{recipeId}/comments - Add comment
router.post('/recipes/:recipeId/comments', async (ctx) => {
    const { recipeId } = ctx.params;
    const { comment } = ctx.request.body;

    if (!comment) {
        ctx.status = 400;
        ctx.body = { error: 'Invalid input' };
        return;
    }

    try {
        const recipe = await query('SELECT id FROM recipes WHERE id = ?', [recipeId]);
        if (recipe.length === 0) {
            ctx.status = 404;
            ctx.body = { error: 'Recipe not found' };
            return;
        }
        await run('INSERT INTO comments (recipeId, comment) VALUES (?, ?)', [recipeId, comment]);
        ctx.status = 201;
    } catch (e) {
        ctx.status = 500;
        ctx.body = { error: 'Database error' };
    }
});

// POST /recipes/{recipeId}/ratings - Rate recipe
router.post('/recipes/:recipeId/ratings', async (ctx) => {
    const { recipeId } = ctx.params;
    const { rating } = ctx.request.body;

    if (rating === undefined || !Number.isInteger(rating) || rating < 1 || rating > 5) {
        ctx.status = 400;
        ctx.body = { error: 'Invalid input: rating must be an integer between 1 and 5' };
        return;
    }

    try {
        const recipe = await query('SELECT id FROM recipes WHERE id = ?', [recipeId]);
        if (recipe.length === 0) {
            ctx.status = 404;
            ctx.body = { error: 'Recipe not found' };
            return;
        }
        await run('INSERT INTO ratings (recipeId, rating) VALUES (?, ?)', [recipeId, rating]);
        ctx.status = 201;
    } catch (e) {
        ctx.status = 500;
        ctx.body = { error: 'Database error' };
    }
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});