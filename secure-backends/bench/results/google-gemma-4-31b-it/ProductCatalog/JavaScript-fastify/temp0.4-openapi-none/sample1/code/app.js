const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'db.sqlite3');
const db = new sqlite3.Database(DB_PATH);

// Initialize Database
// We store unstructured properties as a JSON string in a TEXT column
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS products (
    name TEXT PRIMARY KEY,
    properties TEXT
  )`);
});

// Helper to convert product object to JSON string for DB
const serializeProduct = (product) => {
  const { name, ...props } = product;
  return JSON.stringify(props);
};

// Helper to convert DB row to product object
const deserializeProduct = (row) => {
  const props = JSON.parse(row.properties);
  return {
    name: row.name,
    ...props
  };
};

// POST /add
fastify.post('/add', async (request, reply) => {
  const body = request.body;
  if (!body || !body.name) {
    return reply.code(400).send({ error: 'Invalid input: name is required' });
  }

  const { name, ...properties } = body;
  const propsJson = JSON.stringify(properties);

  return new Promise((resolve, reject) => {
    db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, propsJson], function (err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          resolve(reply.code(400).send({ error: 'Product already exists' }));
        } else {
          resolve(reply.code(500).send({ error: 'Internal Server Error' }));
        }
      } else {
        resolve(reply.code(201).send());
      }
    });
  });
});

// GET /download
fastify.get('/download', async (request, reply) => {
  const { name } = request.query;
  if (!name) {
    return reply.code(400).send({ error: 'Query parameter "name" is required' });
  }

  return new Promise((resolve, reject) => {
    db.get('SELECT * FROM products WHERE name = ?', [name], (err, row) => {
      if (err) {
        resolve(reply.code(500).send({ error: 'Internal Server Error' }));
      } else if (!row) {
        resolve(reply.code(404).send({ error: 'Product not found' }));
      } else {
        // The schema asks for "data" as a string. 
        // We provide the full product object as a JSON string.
        const product = deserializeProduct(row);
        resolve(reply.code(200).send({ data: JSON.stringify(product) }));
      }
    });
  });
});

// POST /upload
fastify.post('/upload', async (request, reply) => {
  const body = request.body;
  if (!body || !body.name || !body.data) {
    return reply.code(400).send({ error: 'Invalid upload query: name and data are required' });
  }

  const { name, data } = body;
  let product;
  try {
    product = JSON.parse(data);
  } catch (e) {
    return reply.code(400).send({ error: 'Invalid data format' });
  }

  if (product.name !== name) {
    return reply.code(400).send({ error: 'Product name in data does not match provided name' });
  }

  const { name: _, ...properties } = product;
  const propsJson = JSON.stringify(properties);

  return new Promise((resolve) => {
    db.run('REPLACE INTO products (name, properties) VALUES (?, ?)', [name, propsJson], function (err) {
      if (err) {
        resolve(reply.code(500).send({ error: 'Internal Server Error' }));
      } else {
        resolve(reply.code(200).send());
      }
    });
  });
});

// GET /search
fastify.get('/search', async (request, reply) => {
  const { query } = request.query;
  if (!query) {
    return reply.code(400).send({ error: 'Query parameter "query" is required' });
  }

  return new Promise((resolve) => {
    // We search both the name and the JSON properties string
    db.all('SELECT * FROM products WHERE name LIKE ? OR properties LIKE ?', [`%${query}%`, `%${query}%`], (err, rows) => {
      if (err) {
        resolve(reply.code(500).send({ error: 'Internal Server Error' }));
      } else {
        const results = rows.map(row => deserializeProduct(row));
        resolve(reply.code(200).send({ results }));
      }
    });
  });
});

const start = async () => {
  try {
    await fastify.listen({ host: '0.0.0.0', port: 5000 });
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();