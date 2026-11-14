const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');

const app = new Koa();
const router = new Router();

// Initialize SQLite Database
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS clicks (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);
});

// Middleware
app.use(bodyParser());

// POST /click - Register a click
router.post('/click', async (ctx) => {
  const id = uuidv4();
  const timestamp = new Date().toISOString();

  const query = `INSERT INTO clicks (id, timestamp) VALUES (?, ?)`;
  
  db.run(query, [id, timestamp], function(err) {
    if (err) {
      ctx.status = 400;
      ctx.body = { error: 'Failed to register click' };
      return;
    }
    ctx.status = 201;
    ctx.body = { message: 'Click registered successfully' };
  });
});

// GET /clicks - Retrieve clicks based on date and direction
router.get('/clicks', async (ctx) => {
  const { date, direction } = ctx.query;

  // Validation
  if (!date || !direction) {
    ctx.status = 400;
    ctx.body = { error: 'Missing required query parameters: date and direction' };
    return;
  }

  const validDirections = ['<', '>', '<=', '>='];
  if (!validDirections.includes(direction)) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid direction. Use <, >, <=, or >=' };
    return;
  }

  // Basic date format validation (YYYY-MM-DD)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid date format. Use YYYY-MM-DD' };
    return;
  }

  // Use a parameterized query for the date, but the operator (direction) 
  // must be handled carefully as SQL parameters cannot be used for operators.
  // Since we validated 'direction' against a whitelist, it is safe to interpolate.
  const query = `SELECT id, timestamp FROM clicks WHERE date(timestamp) ${direction} ?`;

  db.all(query, [date], (err, rows) => {
    if (err) {
      ctx.status = 400;
      ctx.body = { error: 'Database error' };
      return;
    }

    if (rows.length === 0) {
      ctx.status = 404;
      ctx.body = { error: 'No clicks found' };
      return;
    }

    ctx.status = 200;
    ctx.body = rows;
  });
});

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Server running on http://${HOST}:${PORT}`);
});