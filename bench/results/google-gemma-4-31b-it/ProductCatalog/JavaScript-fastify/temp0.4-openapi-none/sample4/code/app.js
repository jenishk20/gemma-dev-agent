const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'db.sqlite3');
const db = new sqlite3.Database(DB_PATH);

// Initialize Database
// We store the product name as the primary key and the unstructured properties as a JSON string
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS products (
    name TEXT PRIMARY KEY,
    properties TEXT
  )`);
});

// Helper to parse and stringify JSON for the database
const serializeProperties = (obj) => JSON.stringify(obj);
const deserializeProperties = (str) => JSON.parse(str);

// Route: /add
fastify.post('/add', async (request, reply) => {
  const body = request.body;
  if (!body || !body.name) {
    return reply.code(400).send({ error: 'Invalid input: name is required' });
  }

  const { name, ...properties } = body;
  const propsJson = serializeProperties(properties);

  return new Promise((resolve, reject) => {
    db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, propsJson], function (err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          resolve(reply.code(400).send({ error: 'Product already exists' }));
        } else {
          resolve(reply.code(500).send({ error: err.message }));
        }
      } else {
        resolve(reply.code(201).send());
      }
    });
  });
});

// Route: /download
fastify.get('/download', async (request, reply) => {
  const { name } = request.query;
  if (!name) {
    return reply.code(400).send({ error: 'Query parameter "name" is required' });
  }

  return new Promise((resolve, reject) => {
    db.get('SELECT properties FROM products WHERE name = ?', [name], (err, row) => {
      if (err) {
        resolve(reply.code(500).send({ error: err.message }));
      } else if (!row) {
        resolve(reply.code(404).send({ error: 'Product not found' }));
      } else {
        // The schema asks for the data as a string in the "data" field
        resolve(reply.code(200).send({ data: row.properties }));
      }
    });
  });
});

// Route: /upload
fastify.post('/upload', async (request, reply) => {
  const { name, data } = request.body;
  if (!name || data === undefined) {
    return reply.code(400).send({ error: 'Invalid upload query: name and data are required' });
  }

  // Validate that data is a valid JSON string of properties
  try {
    JSON.parse(data);
  } catch (e) {
    return reply.code(400).send({ error: 'Invalid data format' });
  }

  return new Promise((resolve, reject) => {
    db.run('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', [name, data], function (err) {
      if (err) {
        resolve(reply.code(500).send({ error: err.message }));
      } else {
        resolve(reply.code(200).send({ message: 'Product updated' }));
      }
    });
  });
});

// Route: /search
fastify.get('/search', async (request, reply) => {
  const { query } = request.query;
  if (!query) {
    return reply.code(400).send({ error: 'Query parameter "query" is required' });
  }

  return new Promise((resolve, reject) => {
    // We search for the query in the name OR the properties JSON string
    db.all('SELECT name, properties FROM products WHERE name LIKE ? OR properties LIKE ?', 
      [`%${query}%`, `%${query}%`], 
      (err, rows) => {
      if (err) {
        resolve(reply.code(500).send({ error: err.message }));
      } else {
        const results = rows.map(row => {
          const props = deserializeProperties(row.properties);
          return {
            name: row.name,
            ...props
          };
        });
        resolve(reply.code(200).send({ results }));
      }
    });
  });
});

// Start Server
const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();