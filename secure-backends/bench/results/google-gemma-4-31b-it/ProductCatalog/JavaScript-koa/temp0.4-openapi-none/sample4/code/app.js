const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = new Koa();
const router = new Router();
const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
// We store the product name as the primary key.
// Unstructured properties are stored as a JSON string in a 'properties' column.
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS products (
    name TEXT PRIMARY KEY,
    properties TEXT
  )`);
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

/**
 * POST /add
 * Adds a new product. 
 * name is required. All other fields are treated as unstructured properties.
 */
router.post('/add', async (ctx) => {
  const body = ctx.request.body;
  if (!body || typeof body !== 'object' || !body.name) {
    ctx.throw(400, 'Invalid input: name is required');
  }

  const { name, ...properties } = body;
  
  // Validate that all additional properties are strings as per schema
  for (const key in properties) {
    if (typeof properties[key] !== 'string') {
      ctx.throw(400, `Property ${key} must be a string`);
    }
  }

  const propsJson = JSON.stringify(properties);

  const query = `INSERT INTO products (name, properties) VALUES (?, ?)`;
  db.run(query, [name, propsJson], function(err) {
    if (err) {
      if (err.message.includes('UNIQUE constraint failed')) {
        ctx.throw(400, 'Product with this name already exists');
      }
      ctx.throw(500, err.message);
    }
    ctx.status = 201;
  });
});

/**
 * GET /download
 * Returns the product data as a JSON string in the 'data' field.
 */
router.get('/download', async (ctx) => {
  const name = ctx.query.name;
  if (!name) {
    ctx.throw(400, 'Query parameter "name" is required');
  }

  db.get(`SELECT * FROM products WHERE name = ?`, [name], (err, row) => {
    if (err) ctx.throw(500, err.message);
    if (!row) ctx.throw(400, 'Product not found');

    // Reconstruct the object to stringify it as the "data" entry
    const productObj = { name: row.name, ...JSON.parse(row.properties) };
    ctx.body = {
      data: JSON.stringify(productObj)
    };
  });
});

/**
 * POST /upload
 * Replaces existing product data.
 */
router.post('/upload', async (ctx) => {
  const body = ctx.request.body;
  if (!body || !body.name || !body.data) {
    ctx.throw(400, 'Invalid upload query: name and data are required');
  }

  let productObj;
  try {
    productObj = JSON.parse(body.data);
  } catch (e) {
    ctx.throw(400, 'Invalid JSON in data field');
  }

  if (!productObj.name || productObj.name !== body.name) {
    ctx.throw(400, 'Data name must match the provided product name');
  }

  const { name, ...properties } = productObj;
  const propsJson = JSON.stringify(properties);

  const query = `INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)`;
  db.run(query, [body.name, propsJson], function(err) {
    if (err) ctx.throw(500, err.message);
    ctx.status = 200;
    ctx.body = { message: 'Product updated' };
  });
});

/**
 * GET /search
 * Searches for products where name or any property contains the query string.
 */
router.get('/search', async (ctx) => {
  const queryStr = ctx.query.query;
  if (!queryStr) {
    ctx.throw(400, 'Query parameter "query" is required');
  }

  // We fetch all and filter in JS because properties are stored as a JSON string in SQLite
  // For a small catalog this is acceptable. For larger, one would use JSON1 extension.
  db.all(`SELECT * FROM products`, [], (err, rows) => {
    if (err) ctx.throw(500, err.message);

    const results = rows.filter(row => {
      const props = JSON.parse(row.properties);
      if (row.name.toLowerCase().includes(queryStr.toLowerCase())) return true;
      
      return Object.values(props).some(val => 
        typeof val === 'string' && val.toLowerCase().includes(queryStr.toLowerCase())
      );
    }).map(row => ({
      name: row.name,
      ...JSON.parse(row.properties)
    }));

    ctx.body = { results };
  });
});

// Start server
app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});