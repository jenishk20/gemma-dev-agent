const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS clicks (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);
});

// Route: Register a click
fastify.post('/click', async (request, reply) => {
  const id = uuidv4();
  const timestamp = new Date().toISOString();

  return new Promise((resolve, reject) => {
    const stmt = db.prepare('INSERT INTO clicks (id, timestamp) VALUES (?, ?)');
    stmt.run(id, timestamp, function (err) {
      if (err) {
        reply.status(400).send({ error: 'Invalid request' });
        return resolve();
      }
      reply.status(201).send();
      resolve();
    });
    stmt.finalize();
  });
});

// Route: Retrieve clicks
fastify.get('/clicks', async (request, reply) => {
  const { date, direction } = request.query;

  // Validation
  if (!date || !direction) {
    return reply.status(400).send({ error: 'Missing required query parameters: date and direction' });
  }

  const allowedDirections = ['<', '>', '<=', '>='];
  if (!allowedDirections.includes(direction)) {
    return reply.status(400).send({ error: 'Invalid direction. Allowed values: <, >, <=, >=' });
  }

  // Simple date format validation (YYYY-MM-DD)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return reply.status(400).send({ error: 'Invalid date format. Expected YYYY-MM-DD' });
  }

  return new Promise((resolve, reject) => {
    // Using a parameterized query for the value, but the operator must be interpolated 
    // because SQL parameters cannot be used for operators. 
    // Since we validated 'direction' against a strict whitelist, this is safe from SQL injection.
    const query = `SELECT id, timestamp FROM clicks WHERE date(timestamp) ${direction} ?`;
    
    db.all(query, [date], (err, rows) => {
      if (err) {
        reply.status(400).send({ error: 'Database error' });
        return resolve();
      }
      
      if (!rows || rows.length === 0) {
        reply.status(404).send({ error: 'No clicks found' });
      } else {
        reply.status(200).send(rows);
      }
      resolve();
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