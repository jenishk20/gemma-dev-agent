const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Initialize SQLite Database
const db = new sqlite3.Database('db.sqlite3');

// Create table to store products. 
// Since we need unstructured properties, we store the 'name' as a primary key 
// and the rest of the properties as a JSON string in a 'properties' column.
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS products (
    name TEXT PRIMARY KEY,
    properties TEXT
  )`);
});

// Helper to wrap db.get/all in promises
const dbGet = (sql, params) => new Promise((res, rej) => {
  db.get(sql, params, (err, row) => err ? rej(err) : res(row));
});
const dbAll = (sql, params) => new Promise((res, rej) => {
  db.all(sql, params, (err, rows) => err ? rej(err) : res(rows));
});
const dbRun = (sql, params) => new Promise((res, rej) => {
  db.run(sql, params, function(err) { err ? rej(err) : res(this); });
});

// --- Routes ---

// POST /add
fastify.post('/add', async (request, reply) => {
  const body = request.body;
  if (!body || typeof body.name !== 'string') {
    return reply.code(400).send({ error: 'Invalid input: name is required' });
  }

  const { name, ...rest } = body;
  const propertiesJson = JSON.stringify(rest);

  try {
    await dbRun('INSERT INTO products (name, properties) VALUES (?, ?)', [name, propertiesJson]);
    return reply.code(201).send();
  } catch (err) {
    if (err.message.includes('UNIQUE constraint failed')) {
      return reply.code(400).send({ error: 'Product with this name already exists' });
    }
    throw err;
  }
});

// GET /download
fastify.get('/download', async (request, reply) => {
  const { name } = request.query;
  if (!name) {
    return reply.code(400).send({ error: 'Query parameter name is required' });
  }

  const row = await dbGet('SELECT properties FROM products WHERE name = ?', [name]);
  if (!row) {
    return reply.code(404).send({ error: 'Product not found' });
  }

  // The schema asks for a response object with a 'data' string containing the product info.
  // We return the JSON string of the properties.
  return { data: row.properties };
});

// POST /upload
fastify.post('/upload', async (request, reply) => {
  const { name, data } = request.body;
  if (!name || typeof data !== 'string') {
    return reply.code(400).send({ error: 'Invalid upload query: name and data are required' });
  }

  try {
    // Validate that data is valid JSON
    JSON.parse(data);
    await dbRun('UPDATE products SET properties = ? WHERE name = ?', [data, name]);
    return reply.code(200).send({ message: 'Product updated' });
  } catch (err) {
    return reply.code(400).send({ error: 'Invalid data format' });
  }
});

// GET /search
fastify.get('/search', async (request, reply) => {
  const { query } = request.query;
  if (!query) {
    return reply.code(400).send({ error: 'Query parameter query is required' });
  }

  // We fetch all products and filter in JS because properties are stored as a JSON string
  // and SQLite's JSON search varies by version. This ensures compatibility.
  const rows = await dbAll('SELECT * FROM products');
  const results = [];

  for (const row of rows) {
    const props = JSON.parse(row.properties || '{}');
    const product = { name: row.name, ...props };
    
    // Check if name or any property value contains the query string (case-insensitive)
    const matches = Object.values(product).some(val => 
      typeof val === 'string' && val.toLowerCase().includes(query.toLowerCase())
    );

    if (matches) {
      results.push(product);
    }
  }

  return { results };
});

// Start Server
fastify.listen({ port: 5000, host: '0.0.0.0' }, (err, address) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log(`Server listening on ${address}`);
});