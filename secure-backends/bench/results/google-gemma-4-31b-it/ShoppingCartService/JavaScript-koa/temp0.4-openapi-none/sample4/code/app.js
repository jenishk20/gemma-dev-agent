const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const app = new Koa();
const router = new Router();
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
const dbQuery = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });
};

const dbGet = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
};

const dbRun = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function(err) {
      if (err) reject(err);
      else resolve(this);
    });
  });
};

// Route: Create Cart
router.post('/create_cart', async (ctx) => {
  const cart_id = uuidv4();
  try {
    await dbRun('INSERT INTO carts (cart_id) VALUES (?)', [cart_id]);
    ctx.status = 201;
    ctx.body = { cart_id };
  } catch (e) {
    ctx.status = 500;
    ctx.body = { error: 'Internal Server Error' };
  }
});

// Route: Add to Cart
router.post('/add_to_cart', async (ctx) => {
  const { cart_id, item_id, count } = ctx.request.body;

  if (!cart_id || item_id === undefined || count === undefined) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid request' };
    return;
  }

  try {
    const cart = await dbGet('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id]);
    if (!cart) {
      ctx.status = 404;
      ctx.body = { error: 'Cart not found' };
      return;
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

    ctx.status = 200;
    ctx.body = { message: 'Item updated successfully' };
  } catch (e) {
    ctx.status = 500;
    ctx.body = { error: 'Internal Server Error' };
  }
});

// Route: Retrieve Cart
router.post('/retrieve_cart', async (ctx) => {
  const { cart_id } = ctx.request.body;

  if (!cart_id) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid request' };
    return;
  }

  try {
    const cart = await dbGet('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id]);
    if (!cart) {
      ctx.status = 404;
      ctx.body = { error: 'Cart not found' };
      return;
    }

    const items = await dbQuery('SELECT item_id, count FROM cart_items WHERE cart_id = ?', [cart_id]);
    ctx.status = 200;
    ctx.body = { items };
  } catch (e) {
    ctx.status = 500;
    ctx.body = { error: 'Internal Server Error' };
  }
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});