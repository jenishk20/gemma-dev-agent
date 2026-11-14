const fastify = require('fastify');
const sqlite3 = require('sqlite3');
const { v4: uuidv4 } = require('uuid');
const path = require('path');

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

// Helper to wrap db.get/all/run in promises
const dbQuery = {
  get: (sql, params) => new Promise((res, rej) => db.get(sql, params, (err, row) => err ? rej(err) : res(row))),
  all: (sql, params) => new Promise((res, rej) => db.all(sql, params, (err, rows) => err ? rej(err) : res(rows))),
  run: (sql, params) => new Promise((res, rej) => db.run(sql, params, function(err) { err ? rej(err) : res(this) }))),
};

// Route: Create Cart
app.post('/create_cart', async (request, reply) => {
  const cart_id = uuidv4();
  try {
    await dbQuery.run('INSERT INTO carts (cart_id) VALUES (?)', [cart_id]);
    return reply.code(201).send({ cart_id });
  } catch (err) {
    return reply.code(500).send({ error: 'Internal Server Error' });
  }
});

// Route: Add/Remove from Cart
app.post('/add_to_cart', async (request, reply) => {
  const { cart_id, item_id, count } = request.body;

  if (cart_id === undefined || item_id === undefined || count === undefined) {
    return reply.code(400).send({ error: 'Missing required fields' });
  }

  try {
    const cart = await dbQuery.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id]);
    if (!cart) {
      return reply.code(404).send({ error: 'Cart not found' });
    }

    // Get current count
    const item = await dbQuery.get('SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?', [cart_id, item_id]);
    const currentCount = item ? item.count : 0;
    const newCount = currentCount + count;

    if (newCount <= 0) {
      // Remove item if count drops to 0 or below
      await dbQuery.run('DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?', [cart_id, item_id]);
    } else {
      // Update or Insert
      await dbQuery.run(
        'INSERT INTO cart_items (cart_id, item_id, count) VALUES (?, ?, ?) ON CONFLICT(cart_id, item_id) DO UPDATE SET count = excluded.count',
        [cart_id, item_id, newCount]
      );
    }

    return reply.code(200).send({ message: 'Item updated successfully' });
  } catch (err) {
    return reply.code(500).send({ error: 'Internal Server Error' });
  }
});

// Route: Retrieve Cart
app.post('/retrieve_cart', async (request, reply) => {
  const { cart_id } = request.body;

  if (!cart_id) {
    return reply.code(400).send({ error: 'cart_id is required' });
  }

  try {
    const cart = await dbQuery.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id]);
    if (!cart) {
      return reply.code(404).send({ error: 'Cart not found' });
    }

    const rows = await dbQuery.all('SELECT item_id, count FROM cart_items WHERE cart_id = ?', [cart_id]);
    
    return reply.code(200).send({
      items: rows.map(row => ({
        item_id: row.item_id,
        count: row.count
      }))
    });
  } catch (err) {
    return reply.code(500).send({ error: 'Internal Server Error' });
  }
});

// Start Server
const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();