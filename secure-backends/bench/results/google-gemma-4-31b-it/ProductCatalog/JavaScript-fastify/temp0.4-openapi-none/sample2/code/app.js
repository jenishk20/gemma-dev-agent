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
const deserializeProduct = (name, propertiesJson) => {
  const props = JSON.parse(propertiesJson || '{}');
  return { name, ...props };
};

// POST /add
fastify.post('/add', async (request, reply) => {
  const body = request.body;
  if (!body || typeof body.name !== 'string') {
    return reply.status(400).send({ error: 'Invalid input: name is required' });
  }

  const propertiesJson = serializeProduct(body);

  return new Promise((resolve, reject) => {
    db.run(
      'INSERT INTO products (name, properties) VALUES (?, ?)',
      [body.name, propertiesJson],
      function (err) {
        if (err) {
          if (err.message.includes('UNIQUE constraint failed')) {
            resolve(reply.status(400).send({ error: 'Product already exists' }));
          } else {
            resolve(reply.status(500).send({ error: 'Database error' }));
          }
        } else {
          resolve(reply.status(201).send());
        }
      }
    );
  });
});

// GET /download
fastify.get('/download', async (request, reply) => {
  const { name } = request.query;
  if (!name) {
    return reply.status(400).send({ error: 'Query parameter "name" is required' });
  }

  return new Promise((resolve) => {
    db.get('SELECT properties FROM products WHERE name = ?', [name], (err, row) => {
      if (err || !row) {
        resolve(reply.status(404).send({ error: 'Product not found' }));
      } else {
        // The schema requires the data to be returned as a string in the 'data' field
        // We return the JSON string of the properties as the "data" entry
        resolve(reply.status(200).send({ data: row.properties }));
      }
    });
  });
});

// POST /upload
fastify.post('/upload', async (request, reply) => {
  const body = request.body;
  if (!body || !body.name || typeof body.data !== 'string') {
    return reply.status(400).send({ error: 'Invalid upload query' });
  }

  return new Promise((resolve) => {
    // Validate that data is valid JSON before updating
    try {
      JSON.parse(body.data);
    } catch (e) {
      return resolve(reply.status(400).send({ error: 'Invalid data format' }));
    }

    db.run(
      'UPDATE products SET properties = ? WHERE name = ?',
      [body.data, body.name],
      function (err) {
        if (err) {
          resolve(reply.status(500).send({ error: 'Database error' }));
        } else if (this.changes === 0) {
          resolve(reply.status(404).send({ error: 'Product not found' }));
        } else {
          resolve(reply.status(200).send({ message: 'Product updated' }));
        }
      }
    );
  });
});

// GET /search
fastify.get('/search', async (request, reply) => {
  const { query } = request.query;
  if (!query) {
    return reply.status(400).send({ error: 'Query parameter "query" is required' });
  }

  return new Promise((resolve) => {
    db.all('SELECT name, properties FROM products', [], (err, rows) => {
      if (err) {
        return resolve(reply.status(500).send({ error: 'Database error' }));
      }

      const results = rows
        .map(row => deserializeProduct(row.name, row.properties))
        .filter(product => {
          // Search in name or any of the unstructured property values
          return Object.values(product).some(val => 
            typeof val === 'string' && val.toLowerCase().includes(query.toLowerCase())
          );
        });

      resolve(reply.status(200).send({ results }));
    });
  });
});

// Start Server
const start = async () => {
  try {
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();