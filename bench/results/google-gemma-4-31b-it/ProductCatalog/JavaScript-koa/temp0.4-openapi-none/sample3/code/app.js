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
// metadata as a JSON string in a TEXT column.
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS products (
    name TEXT PRIMARY KEY,
    properties TEXT
  )`);
});

app.use(bodyParser());

// POST /add
router.post('/add', async (ctx) => {
  const body = ctx.request.body;
  if (!body || typeof body !== 'object' || !body.name) {
    ctx.throw(400, 'Invalid input: name is required');
  }

  const { name, ...properties } = body;
  
  // Validate that all additional properties are strings as per schema
  for (const key in properties) {
    if (typeof properties[key] !== 'string') {
      ctx.throw(400, 'All additional properties must be strings');
    }
  }

  const propsJson = JSON.stringify(properties);

  try {
    await new Promise((resolve, reject) => {
      db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, propsJson], function(err) {
        if (err) reject(err);
        else resolve();
      });
    });
    ctx.status = 201;
  } catch (err) {
    if (err.message.includes('UNIQUE constraint failed')) {
      ctx.throw(400, 'Product with this name already exists');
    }
    ctx.throw(500, 'Internal Server Error');
  }
});

// GET /download
router.get('/download', async (ctx) => {
  const name = ctx.query.name;
  if (!name) {
    ctx.throw(400, 'Query parameter "name" is required');
  }

  const product = await new Promise((resolve, reject) => {
    db.get('SELECT properties FROM products WHERE name = ?', [name], (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });

  if (!product) {
    ctx.throw(404, 'Product not found');
  }

  // The schema says it returns an object with a 'data' property containing the product data as a string
  ctx.body = {
    data: product.properties
  };
});

// POST /upload
router.post('/upload', async (ctx) => {
  const body = ctx.request.body;
  if (!body || !body.name || !body.data) {
    ctx.throw(400, 'Invalid upload query: name and data are required');
  }

  const { name, data } = body;

  // Validate that data is a valid JSON string of string-properties
  try {
    const parsed = JSON.parse(data);
    for (const key in parsed) {
      if (typeof parsed[key] !== 'string') throw new Error();
    }
  } catch (e) {
    ctx.throw(400, 'Invalid data format');
  }

  await new Promise((resolve, reject) => {
    db.run('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', [name, data], function(err) {
      if (err) reject(err);
      else resolve();
    });
  });

  ctx.status = 200;
  ctx.body = { message: 'The product with the given name was updated.' };
});

// GET /search
router.get('/search', async (ctx) => {
  const query = ctx.query.query;
  if (!query) {
    ctx.throw(400, 'Query parameter "query" is required');
  }

  const results = await new Promise((resolve, reject) => {
    // We fetch all and filter in JS because the properties are stored as a JSON string
    db.all('SELECT * FROM products', [], (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });

  const filtered = results.filter(row => {
    const props = JSON.parse(row.properties || '{}');
    // Match name
    if (row.name.toLowerCase().includes(query.toLowerCase())) return true;
    // Match any property value
    for (const key in props) {
      if (props[key].toLowerCase().includes(query.toLowerCase())) return true;
    }
    return false;
  }).map(row => {
    return {
      name: row.name,
      ...JSON.parse(row.properties || '{}')
    };
  });

  ctx.body = { results: filtered };
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});