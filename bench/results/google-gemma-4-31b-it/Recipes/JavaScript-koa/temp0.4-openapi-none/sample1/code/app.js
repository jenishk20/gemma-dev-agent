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

app.use(bodyParser());

// Helper to wrap db.get/all in promises
const dbGet = (query, params = []) => new Promise((res, rej) => {
  db.get(query, params, (err, row) => err ? rej(err) : res(row));
});
const dbAll = (query, params = []) => new Promise((res, rej) => {
  db.all(query, params, (err, rows) => err ? rej(err) : res(rows));
});
const dbRun = (query, params = []) => new Promise((res, rej) => {
  db.run(query, params, function(err) { err ? rej(err) : res(this); });
});

// GET /recipes - Overview of recipes
router.get('/recipes', async (ctx) => {
  try {
    const recipes = await dbAll('SELECT id, title FROM recipes');
    let html = '<h1>Recipe Overview</h1><ul>';
    recipes.forEach(r => {
      html += `<li><a href="/recipes/${r.id}">${r.title}</a></li>`;
    });
    html += '</ul>';
    ctx.type = 'text/html';
    ctx.body = html;
  } catch (e) {
    ctx.status = 500;
    ctx.body = 'Server Error';
  }
});

// POST /recipes/upload - Upload a new recipe
router.post('/recipes/upload', async (ctx) => {
  const { title, ingredients, instructions } = ctx.request.body;
  if (!title || !ingredients || !instructions) {
    ctx.status = 400;
    ctx.body = 'Invalid input';
    return;
  }

  const id = uuidv4();
  const ingredientsJson = JSON.stringify(ingredients);
  
  try {
    await dbRun('INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)', 
      [id, title, ingredientsJson, instructions]);
    
    ctx.status = 201;
    ctx.body = {
      id,
      title,
      ingredients,
      instructions,
      comments: [],
      avgRating: null
    };
  } catch (e) {
    ctx.status = 500;
  }
});

// GET /recipes/{recipeId} - Get a recipe
router.get('/recipes/:recipeId', async (ctx) => {
  const { recipeId } = ctx.params;
  try {
    const recipe = await dbGet('SELECT * FROM recipes WHERE id = ?', [recipeId]);
    if (!recipe) {
      ctx.status = 404;
      return;
    }

    const comments = await dbAll('SELECT comment FROM comments WHERE recipeId = ?', [recipeId]);
    const ratings = await dbAll('SELECT rating FROM ratings WHERE recipeId = ?', [recipeId]);
    
    const avgRating = ratings.length > 0 
      ? ratings.reduce((acc, curr) => acc + curr.rating, 0) / ratings.length 
      : null;

    const ingredients = JSON.parse(recipe.ingredients);

    // The schema specifies text/html for this endpoint
    let html = `<h1>${recipe.title}</h1>`;
    html += `<p><strong>Ingredients:</strong> ${ingredients.join(', ')}</p>`;
    html += `<p><strong>Instructions:</strong> ${recipe.instructions}</p>`;
    html += `<p><strong>Average Rating:</strong> ${avgRating !== null ? avgRating.toFixed(2) : 'No ratings yet'}</p>`;
    html += `<h3>Comments</h3><ul>`;
    comments.forEach(c => { html += `<li>${c.comment}</li>`; });
    html += `</ul>`;
    html += `<hr><a href="/recipes">Back to Overview</a>`;

    ctx.type = 'text/html';
    ctx.body = html;
  } catch (e) {
    ctx.status = 500;
  }
});

// POST /recipes/{recipeId}/comments - Add a comment
router.post('/recipes/:recipeId/comments', async (ctx) => {
  const { recipeId } = ctx.params;
  const { comment } = ctx.request.body;

  if (!comment) {
    ctx.status = 400;
    return;
  }

  const recipe = await dbGet('SELECT id FROM recipes WHERE id = ?', [recipeId]);
  if (!recipe) {
    ctx.status = 404;
    return;
  }

  try {
    await dbRun('INSERT INTO comments (recipeId, comment) VALUES (?, ?)', [recipeId, comment]);
    ctx.status = 201;
  } catch (e) {
    ctx.status = 500;
  }
});

// POST /recipes/{recipeId}/ratings - Rate a recipe
router.post('/recipes/:recipeId/ratings', async (ctx) => {
  const { recipeId } = ctx.params;
  const { rating } = ctx.request.body;

  if (rating === undefined || !Number.isInteger(rating) || rating < 1 || rating > 5) {
    ctx.status = 400;
    return;
  }

  const recipe = await dbGet('SELECT id FROM recipes WHERE id = ?', [recipeId]);
  if (!recipe) {
    ctx.status = 404;
    return;
  }

  try {
    await dbRun('INSERT INTO ratings (recipeId, rating) VALUES (?, ?)', [recipeId, rating]);
    ctx.status = 201;
  } catch (e) {
    ctx.status = 500;
  }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});