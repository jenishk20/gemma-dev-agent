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
    recipeId TEXT NOT NULL,
    comment TEXT NOT NULL,
    FOREIGN KEY(recipeId) REFERENCES recipes(id)
  )`);

  db.run(`CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipeId TEXT NOT NULL,
    rating INTEGER NOT NULL,
    FOREIGN KEY(recipeId) REFERENCES recipes(id)
  )`);
});

app.use(bodyParser());

// GET /recipes - Overview of recipes
router.get('/recipes', async (ctx) => {
  db.all('SELECT id, title FROM recipes', [], (err, rows) => {
    if (err) {
      ctx.status = 500;
      ctx.body = 'Internal Server Error';
      return;
    }
    let html = '<h1>Recipe Overview</h1><ul>';
    rows.forEach(row => {
      html += `<li><a href="/recipes/${row.id}">${row.title}</a></li>`;
    });
    html += '</ul>';
    ctx.type = 'text/html';
    ctx.body = html;
  });
});

// POST /recipes/upload - Upload a new recipe
router.post('/recipes/upload', async (ctx) => {
  const { title, ingredients, instructions } = ctx.request.body;

  if (!title || !ingredients || !instructions || !Array.isArray(ingredients)) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid input' };
    return;
  }

  const id = uuidv4();
  const ingredientsJson = JSON.stringify(ingredients);

  db.run('INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)', 
    [id, title, ingredientsJson, instructions], 
    function(err) {
      if (err) {
        ctx.status = 500;
        ctx.body = { error: 'Database error' };
        return;
      }
      ctx.status = 201;
      ctx.body = { id, title, ingredients, instructions };
    }
  );
});

// GET /recipes/{recipeId} - Get a recipe
router.get('/recipes/:recipeId', async (ctx) => {
  const recipeId = ctx.params.recipeId;

  db.get('SELECT * FROM recipes WHERE id = ?', [recipeId], (err, recipe) => {
    if (err || !recipe) {
      ctx.status = recipe ? 500 : 404;
      ctx.body = recipe ? 'Server Error' : 'Recipe not found';
      return;
    }

    db.all('SELECT comment FROM comments WHERE recipeId = ?', [recipeId], (err, comments) => {
      db.all('SELECT rating FROM ratings WHERE recipeId = ?', [recipeId], (err, ratings) => {
        const avgRating = ratings.length > 0 
          ? ratings.reduce((acc, curr) => acc + curr.rating, 0) / ratings.length 
          : null;

        const ingredients = JSON.parse(recipe.ingredients);
        
        let html = `<h1>${recipe.title}</h1>`;
        html += `<h3>Ingredients</h3><ul>${ingredients.map(i => `<li>${i}</li>`).join('')}</ul>`;
        html += `<h3>Instructions</h3><p>${recipe.instructions}</p>`;
        html += `<p><strong>Average Rating:</strong> ${avgRating ? avgRating.toFixed(1) : 'No ratings yet'}</p>`;
        html += `<h3>Comments</h3><ul>${comments.map(c => `<li>${c.comment}</li>`).join('')}</ul>`;
        html += `<hr><a href="/recipes">Back to Overview</a>`;

        ctx.type = 'text/html';
        ctx.body = html;
      });
    });
  });
});

// POST /recipes/{recipeId}/comments - Add a comment
router.post('/recipes/:recipeId/comments', async (ctx) => {
  const recipeId = ctx.params.recipeId;
  const { comment } = ctx.request.body;

  if (!comment) {
    ctx.status = 400;
    ctx.body = { error: 'Comment is required' };
    return;
  }

  db.get('SELECT id FROM recipes WHERE id = ?', [recipeId], (err, row) => {
    if (!row) {
      ctx.status = 404;
      ctx.body = { error: 'Recipe not found' };
      return;
    }

    db.run('INSERT INTO comments (recipeId, comment) VALUES (?, ?)', [recipeId, comment], (err) => {
      if (err) {
        ctx.status = 500;
        return;
      }
      ctx.status = 201;
      ctx.body = { message: 'Comment added successfully' };
    });
  });
});

// POST /recipes/{recipeId}/ratings - Rate a recipe
router.post('/recipes/:recipeId/ratings', async (ctx) => {
  const recipeId = ctx.params.recipeId;
  const { rating } = ctx.request.body;

  if (typeof rating !== 'number' || rating < 1 || rating > 5) {
    ctx.status = 400;
    ctx.body = { error: 'Rating must be an integer between 1 and 5' };
    return;
  }

  db.get('SELECT id FROM recipes WHERE id = ?', [recipeId], (err, row) => {
    if (!row) {
      ctx.status = 404;
      ctx.body = { error: 'Recipe not found' };
      return;
    }

    db.run('INSERT INTO ratings (recipeId, rating) VALUES (?, ?)', [recipeId, rating], (err) => {
      if (err) {
        ctx.status = 500;
        return;
      }
      ctx.status = 201;
      ctx.body = { message: 'Rating added successfully' };
    });
  });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});