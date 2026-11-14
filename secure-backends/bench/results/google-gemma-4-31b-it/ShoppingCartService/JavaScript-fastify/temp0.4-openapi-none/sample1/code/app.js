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

// Helper to wrap db.get/run in promises
const dbGet = (query, params) => new Promise((res, rej) => {
  db.get(query, params, (err, row) => err ? rej(err) : res(row));
});

const dbRun = (query, params) => new Promise((res, rej) => {
  db.run(query, params, function(err) { err ? rej(err) : res(this); });
});

const dbAll = (query, params) => new Promise((res, rej) => {
  db.all(query, params, (err, rows) => err ? rej(err) : res(rows));
});

// Route: Create Cart
app.post('/create_cart', async (request, reply) => {
  const cart_id = uuidv4();
  try {
    await dbRun('INSERT INTO carts (cart_id) VALUES (?)', [cart_id]);
    return reply.status(201).send({ cart_id });
  } catch (err) {
    return reply.status(500).send({ error: 'Internal Server Error' });
  }
});

// Route: Add to Cart
app.post('/add_to_cart', async (request, reply) => {
  const { cart_id, item_id, count } = request.body;

  if (!cart_id || item_id === undefined || count === undefined) {
    return reply.status(400).send({ error: 'Invalid request' });
  }

  try {
    const cart = await dbGet('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id]);
    if (!cart) {
      return reply.status(404).send({ error: 'Cart not found' });
    }

    const item = await dbGet('SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?', [cart_id, item_id]);
    const currentCount = item ? item.count : 0;
    const newCount = currentCount + count;

    if (newCount <= 0) {
      await dbRun('DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?', [cart_id, item_id]);
    } else {
      await dbRun(
        'INSERT INTO cart_items (cart_id, item_id, count) VALUES (?, ?, ?) ON CONFLICT(cart_id, item_id) DO UPDATE SET count = ?',
        [cart_id, item_id, newCount, newCount]
      );
    }

    return reply.status(200).send({ message: 'Item updated successfully' });
  } catch (err) {
    return reply.status(500).send({ error: 'Internal Server Error' });
  }
});

// Route: Retrieve Cart
app.post('/retrieve_cart', async (request, reply) => {
  const { cart_id } = request.body;

  if (!cart_id) {
    return reply.status(400).send({ error: 'Invalid request' });
  }

  try {
    const cart = await dbGet('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id]);
    if (!cart) {
      return reply.status(404).send({ error: 'Cart not found' });
    }

    const items = await dbAll('SELECT item_id, count FROM cart_items WHERE cart_id = ?', [cart_id]);
    return reply.status(200).send({ items });
  } catch (err) {
    return reply.status(500).send({ error: 'Internal Server Error' });
  }
});

// Start Server
const start = async () => {
  try {
    await app.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();