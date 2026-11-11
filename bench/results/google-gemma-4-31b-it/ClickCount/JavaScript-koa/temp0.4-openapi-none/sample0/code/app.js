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
  db.run(`CREATE TABLE IF NOT EXISTS clicks (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);
});

app.use(bodyParser());

/**
 * POST /click
 * Register a click
 */
router.post('/click', async (ctx) => {
  const id = uuidv4();
  const timestamp = new Date().toISOString();

  const query = `INSERT INTO clicks (id, timestamp) VALUES (?, ?)`;
  
  db.run(query, [id, timestamp], (err) => {
    if (err) {
      ctx.status = 400;
      ctx.body = { error: 'Invalid request' };
      return;
    }
    ctx.status = 201;
    ctx.body = { message: 'Click registered successfully' };
  });
});

/**
 * GET /clicks
 * Retrieve clicks based on date and direction
 */
router.get('/clicks', async (ctx) => {
  const { date, direction } = ctx.query;

  // Validation
  const validDirections = ['<', '>', '<=', '>='];
  if (!date || !direction || !validDirections.includes(direction)) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid request. Please provide date (YYYY-MM-DD) and direction (<, >, <=, >=)' };
    return;
  }

  // Basic date format validation (YYYY-MM-DD)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid date format. Expected YYYY-MM-DD' };
    return;
  }

  // Note: Using template literal for the operator because operators cannot be parameterized in SQL
  // Since we validate 'direction' against a strict whitelist, this is safe from SQL injection.
  const query = `SELECT id, timestamp FROM clicks WHERE date(timestamp) ${direction} ?`;

  db.all(query, [date], (err, rows) => {
    if (err) {
      ctx.status = 400;
      ctx.body = { error: 'Database error' };
      return;
    }

    if (!rows || rows.length === 0) {
      ctx.status = 404;
      ctx.body = { error: 'No clicks found' };
      return;
    }

    ctx.status = 200;
    ctx.body = rows;
  });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});