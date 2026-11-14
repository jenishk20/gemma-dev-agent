const fastify = require('fastify');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = fastify({ logger: true });
const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
db.serialize(() => {
  // We store the 'name' as a primary key and the rest of the properties as a JSON string
  db.run(`CREATE TABLE IF NOT EXISTS products (
    name TEXT PRIMARY KEY,
    properties TEXT
  )`);
});

// Helper to parse/stringify JSON for SQLite
const serializeProps = (obj) => JSON.stringify(obj);
const deserializeProps = (str) => JSON.parse(str);

// POST /add
app.post('/add', async (request, reply) => {
  const body = request.body;
  if (!body || typeof body !== 'object' || !body.name) {
    return reply.code(400).send({ error: 'Invalid input: name is required' });
  }

  const { name, ...extra } = body;
  
  // Ensure all additional properties are strings as per OpenAPI schema
  for (const key in extra) {
    if (typeof extra[key] !== 'string') {
      return reply.code(400).send({ error: `Property ${key} must be a string` });
    }
  }

  const propsJson = serializeProps(extra);

  return new Promise((resolve, reject) => {
    db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, propsJson], function(err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          resolve(reply.code(400).send({ error: 'Product name already exists' }));
        } else {
          resolve(reply.code(500).send({ error: err.message }));
        }
      } else {
        resolve(reply.code(201).send());
      }
    });
  });
});

// GET /download
app.get('/download', async (request, reply) => {
  const { name } = request.query;
  if (!name) {
    return reply.code(400).send({ error: 'Query parameter "name" is required' });
  }

  return new Promise((resolve) => {
    db.get('SELECT name, properties FROM products WHERE name = ?', [name], (err, row) => {
      if (err || !row) {
        resolve(reply.code(400).send({ error: 'Product not found' }));
      } else {
        // The schema asks for a "data" string containing the product entry
        // We combine name and properties into a single JSON string for the 'data' field
        const fullProduct = { name: row.name, ...deserializeProps(row.properties) };
        resolve(reply.code(200).send({ data: JSON.stringify(fullProduct) }));
      }
    });
  });
});

// POST /upload
app.post('/upload', async (request, reply) => {
  const body = request.body;
  if (!body || !body.name || !body.data) {
    return reply.code(400).send({ error: 'Invalid upload query: name and data are required' });
  }

  try {
    const productData = JSON.parse(body.data);
    if (!productData.name || productData.name !== body.name) {
      throw new Error('Data name mismatch');
    }

    const { name, ...extra } = productData;
    const propsJson = serializeProps(extra);

    return new Promise((resolve) => {
      db.run('REPLACE INTO products (name, properties) VALUES (?, ?)', [name, propsJson], function(err) {
        if (err) {
          resolve(reply.code(500).send({ error: err.message }));
        } else {
          resolve(reply.code(200).send({ message: 'Product updated' }));
        }
      });
    });
  } catch (e) {
    return reply.code(400).send({ error: 'Invalid data format' });
  }
});

// GET /search
app.get('/search', async (request, reply) => {
  const { query } = request.query;
  if (!query) {
    return reply.code(400).send({ error: 'Query parameter "query" is required' });
  }

  return new Promise((resolve) => {
    // We search in the name column OR the properties JSON blob
    db.all('SELECT name, properties FROM products WHERE name LIKE ? OR properties LIKE ?', 
      [`%${query}%`, `%${query}%`], 
      (err, rows) => {
        if (err) {
          resolve(reply.code(500).send({ error: err.message }));
        } else {
          const results = rows.map(row => ({
            name: row.name,
            ...deserializeProps(row.properties)
          }));
          resolve(reply.code(200).send({ results }));
        }
      }
    );
  });
});

// Start server
app.listen({ port: 5000, host: '0.0.0.0' }, (err) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log('Server listening on http://0.0.0.0:5000');
});