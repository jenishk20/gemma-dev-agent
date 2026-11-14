const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = new Koa();
const router = new Router();
const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
// Since we need to support "unstructured properties", we store the product 
// as a JSON string in a column, while keeping the 'name' as a separate indexed column for fast lookup.
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS products (
    name TEXT PRIMARY KEY,
    data TEXT
  )`);
});

app.use(bodyParser());

/**
 * POST /add
 * Adds a new product. 
 * The request body is an object where 'name' is required and other fields are unstructured.
 */
router.post('/add', async (ctx) => {
  const body = ctx.request.body;
  if (!body || typeof body !== 'object' || !body.name) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid input: name is required' };
    return;
  }

  const { name, ...properties } = body;
  // Store the whole object (including name) as a JSON string to satisfy the /download requirement
  const dataString = JSON.stringify(body);

  db.run('INSERT INTO products (name, data) VALUES (?, ?)', [name, dataString], function(err) {
    if (err) {
      if (err.message.includes('UNIQUE constraint failed')) {
        ctx.status = 400;
        ctx.body = { error: 'Product with this name already exists' };
      } else {
        ctx.status = 500;
        ctx.body = { error: 'Database error' };
      }
    } else {
      ctx.status = 201;
    }
  });
});

/**
 * GET /download
 * Returns the product data as a string.
 */
router.get('/download', async (ctx) => {
  const name = ctx.query.name;
  if (!name) {
    ctx.status = 400;
    ctx.body = { error: 'Query parameter "name" is required' };
    return;
  }

  db.get('SELECT data FROM products WHERE name = ?', [name], (err, row) => {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Database error' };
    } else if (!row) {
      ctx.status = 404;
      ctx.body = { error: 'Product not found' };
    } else {
      ctx.status = 200;
      ctx.body = { data: row.data };
    }
  });
});

/**
 * POST /upload
 * Replaces existing product data.
 */
router.post('/upload', async (ctx) => {
  const body = ctx.request.body;
  if (!body || !body.name || !body.data) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid upload query: name and data are required' };
    return;
  }

  // Validate that data is a valid JSON string representing the product
  try {
    JSON.parse(body.data);
  } catch (e) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid data format' };
    return;
  }

  db.run('UPDATE products SET data = ? WHERE name = ?', [body.data, body.name], function(err) {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Database error' };
    } else if (this.changes === 0) {
      ctx.status = 400;
      ctx.body = { error: 'Product not found' };
    } else {
      ctx.status = 200;
      ctx.body = { message: 'Product updated' };
    }
  });
});

/**
 * GET /search
 * Searches for products where the query matches name or any property value.
 */
router.get('/search', async (ctx) => {
  const query = ctx.query.query;
  if (!query) {
    ctx.status = 400;
    ctx.body = { error: 'Query parameter "query" is required' };
    return;
  }

  // We fetch all products and filter in JS because the unstructured data is stored as JSON strings
  db.all('SELECT data FROM products', [], (err, rows) => {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Database error' };
      return;
    }

    const results = [];
    rows.forEach(row => {
      const product = JSON.parse(row.data);
      // Check if any value in the product object matches the query string
      const matches = Object.values(product).some(val => 
        String(val).toLowerCase().includes(query.toLowerCase())
      );
      if (matches) {
        results.push(product);
      }
    });

    ctx.status = 200;
    ctx.body = { results };
  });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});