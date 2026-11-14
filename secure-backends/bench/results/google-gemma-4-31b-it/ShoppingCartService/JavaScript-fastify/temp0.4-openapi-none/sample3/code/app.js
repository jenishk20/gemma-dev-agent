const fastify = require('fastify');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const app = fastify({ logger: true });
const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS carts (
    cart_id TEXT PRIMARY KEY
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS cart_items (
    cart_id TEXT,
    item_id INTEGER,
    count INTEGER,
    PRIMARY KEY (cart_id, item_id),
    FOREIGN KEY (cart_id) REFERENCES carts(cart_id)
  )`);
});

// Route: Create Cart
app.post('/create_cart', async (request, reply) => {
  const cart_id = uuidv4();
  
  return new Promise((resolve, reject) => {
    db.run('INSERT INTO carts (cart_id) VALUES (?)', [cart_id], function (err) {
      if (err) {
        reply.status(500).send({ error: 'Database error' });
        return resolve();
      }
      reply.status(201).send({ cart_id });
      resolve();
    });
  });
});

// Route: Add to Cart
app.post('/add_to_cart', async (request, reply) => {
  const { cart_id, item_id, count } = request.body;

  if (!cart_id || item_id === undefined || count === undefined) {
    return reply.status(400).send({ error: 'Invalid request' });
  }

  return new Promise((resolve, reject) => {
    // Check if cart exists
    db.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id], (err, row) => {
      if (err) {
        reply.status(500).send({ error: 'Database error' });
        return resolve();
      }
      if (!row) {
        reply.status(404).send({ error: 'Cart not found' });
        return resolve();
      }

      // Update or Insert item count
      db.run(
        `INSERT INTO cart_items (cart_id, item_id, count) 
         VALUES (?, ?, ?) 
         ON CONFLICT(cart_id, item_id) DO UPDATE SET count = count + excluded.count`,
        [cart_id, item_id, count],
        function (err) {
          if (err) {
            reply.status(500).send({ error: 'Database error' });
            return resolve();
          }

          // Clean up items with count <= 0
          db.run('DELETE FROM cart_items WHERE cart_id = ? AND count <= 0', [cart_id], (err) => {
            reply.status(200).send({ message: 'Item updated successfully' });
            resolve();
          });
        }
      );
    });
  });
});

// Route: Retrieve Cart
app.post('/retrieve_cart', async (request, reply) => {
  const { cart_id } = request.body;

  if (!cart_id) {
    return reply.status(400).send({ error: 'Invalid request' });
  }

  return new Promise((resolve, reject) => {
    // Check if cart exists
    db.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id], (err, row) => {
      if (err) {
        reply.status(500).send({ error: 'Database error' });
        return resolve();
      }
      if (!row) {
        reply.status(404).send({ error: 'Cart not found' });
        return resolve();
      }

      // Get items
      db.all('SELECT item_id, count FROM cart_items WHERE cart_id = ?', [cart_id], (err, rows) => {
        if (err) {
          reply.status(500).send({ error: 'Database error' });
          return resolve();
        }
        reply.status(200).send({ items: rows });
        resolve();
      });
    });
  });
});

// Start Server
const start = async () => {
  try {
    await app.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();