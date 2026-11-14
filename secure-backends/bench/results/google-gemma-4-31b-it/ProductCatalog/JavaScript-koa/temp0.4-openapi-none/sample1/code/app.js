const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = new Koa();
const router = new Router();
const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
// We store the product name as the primary key and the unstructured properties as a JSON string
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS products (
    name TEXT PRIMARY KEY,
    properties TEXT
  )`);
});

app.use(bodyParser());

// POST /add: Add a new product
router.post('/add', async (ctx) => {
  const body = ctx.request.body;
  if (!body || typeof body !== 'object' || !body.name) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid input: name is required' };
    return;
  }

  const { name, ...properties } = body;
  const propsString = JSON.stringify(properties);

  db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, propsString], function(err) {
    if (err) {
      if (err.message.includes('UNIQUE constraint failed')) {
        ctx.status = 400;
        ctx.body = { error: 'Product with this name already exists' };
      } else {
        ctx.status = 500;
        ctx.body = { error: 'Internal server error' };
      }
    } else {
      ctx.status = 201;
    }
  });
});

// GET /download: Download product data
router.get('/download', async (ctx) => {
  const name = ctx.query.name;
  if (!name) {
    ctx.status = 400;
    ctx.body = { error: 'Query parameter "name" is required' };
    return;
  }

  db.get('SELECT properties FROM products WHERE name = ?', [name], (err, row) => {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Internal server error' };
    } else if (!row) {
      ctx.status = 404;
      ctx.body = { error: 'Product not found' };
    } else {
      ctx.status = 200;
      ctx.body = { data: row.properties };
    }
  });
});

// POST /upload: Update product data
router.post('/upload', async (ctx) => {
  const body = ctx.request.body;
  if (!body || typeof body !== 'object' || !body.name || !body.data) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid upload query: name and data are required' };
    return;
  }

  const { name, data } = body;

  // Validate that data is a valid JSON string (as it should be the format returned by /download)
  try {
    JSON.parse(data);
  } catch (e) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid data format' };
    return;
  }

  db.run('UPDATE products SET properties = ? WHERE name = ?', [data, name], function(err) {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Internal server error' };
    } else if (this.changes === 0) {
      ctx.status = 400;
      ctx.body = { error: 'Product not found' };
    } else {
      ctx.status = 200;
      ctx.body = { message: 'The product with the given name was updated.' };
    }
  });
});

// GET /search: Search for products
router.get('/search', async (ctx) => {
  const query = ctx.query.query;
  if (!query) {
    ctx.status = 400;
    ctx.body = { error: 'Query parameter "query" is required' };
    return;
  }

  // Search in name or within the JSON properties string
  const sql = 'SELECT name, properties FROM products WHERE name LIKE ? OR properties LIKE ?';
  const searchTerm = `%${query}%`;

  db.all(sql, [searchTerm, searchTerm], (err, rows) => {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Internal server error' };
      return;
    }

    const results = rows.map(row => {
      const props = JSON.parse(row.properties || '{}');
      return {
        name: row.name,
        ...props
      };
    });

    ctx.status = 200;
    ctx.body = { results };
  });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});