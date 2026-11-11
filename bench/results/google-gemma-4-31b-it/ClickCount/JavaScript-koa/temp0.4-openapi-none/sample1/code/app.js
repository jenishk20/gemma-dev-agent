const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');

const app = new Koa();
const router = new Router();
const PORT = 5000;
const HOST = '0.0.0.0';

// Database Initialization
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS clicks (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);
});

app.use(bodyParser());

/**
 * POST /click
 * Registers a user's click in the database.
 */
router.post('/click', async (ctx) => {
  const id = uuidv4();
  const timestamp = new Date().toISOString();

  return new Promise((resolve, reject) => {
    db.run('INSERT INTO clicks (id, timestamp) VALUES (?, ?)', [id, timestamp], function(err) {
      if (err) {
        ctx.status = 400;
        ctx.body = { error: 'Invalid request' };
        resolve();
      } else {
        ctx.status = 201;
        ctx.body = { message: 'Click registered successfully' };
        resolve();
      }
    });
  });
});

/**
 * GET /clicks
 * Retrieves clicks based on date and direction.
 * Parameters: date (YYYY-MM-DD), direction (<, <=, >, >=)
 */
router.get('/clicks', async (ctx) => {
  const { date, direction } = ctx.query;

  // Validation
  const validDirections = ['<', '>', '<=', '>='];
  if (!date || !direction || !validDirections.includes(direction)) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid request. Please provide a valid date and direction.' };
    return;
  }

  // Basic date format validation (YYYY-MM-DD)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid date format. Use YYYY-MM-DD.' };
    return;
  }

  return new Promise((resolve, reject) => {
    // We use a parameterized query for the date, but the operator (direction) 
    // must be white-listed and interpolated because SQL parameters cannot be operators.
    const query = `SELECT id, timestamp FROM clicks WHERE date(timestamp) ${direction} ?`;
    
    db.all(query, [date], (err, rows) => {
      if (err) {
        ctx.status = 400;
        ctx.body = { error: 'Database error' };
        resolve();
      } else if (rows.length === 0) {
        ctx.status = 404;
        ctx.body = { error: 'No clicks found' };
        resolve();
      } else {
        ctx.status = 200;
        ctx.body = rows;
        resolve();
      }
    });
  });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(PORT, HOST, () => {
  console.log(`Server running on http://${HOST}:${PORT}`);
});