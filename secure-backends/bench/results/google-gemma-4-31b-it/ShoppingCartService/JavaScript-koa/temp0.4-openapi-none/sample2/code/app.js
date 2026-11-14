const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');

const app = new Koa();
const router = new Router();

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

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

app.use(bodyParser());

// POST /create_cart
router.post('/create_cart', async (ctx) => {
  const cart_id = uuidv4();
  
  const promise = new Promise((resolve, reject) => {
    db.run('INSERT INTO carts (cart_id) VALUES (?)', [cart_id], function(err) {
      if (err) reject(err);
      else resolve();
    });
  });

  try {
    await promise;
    ctx.status = 201;
    ctx.body = { cart_id };
  } catch (err) {
    ctx.status = 500;
    ctx.body = { error: 'Internal Server Error' };
  }
});

// POST /add_to_cart
router.post('/add_to_cart', async (ctx) => {
  const { cart_id, item_id, count } = ctx.request.body;

  if (!cart_id || item_id === undefined || count === undefined) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid request' };
    return;
  }

  // Check if cart exists
  const cartExists = await new Promise((resolve) => {
    db.get('SELECT 1 FROM carts WHERE cart_id = ?', [cart_id], (err, row) => {
      resolve(row);
    });
  });

  if (!cartExists) {
    ctx.status = 404;
    ctx.body = { error: 'Cart not found' };
    return;
  }

  const updatePromise = new Promise((resolve, reject) => {
    db.run(
      `INSERT INTO cart_items (cart_id, item_id, count) 
       VALUES (?, ?, ?) 
       ON CONFLICT(cart_id, item_id) DO UPDATE SET count = count + excluded.count`,
      [cart_id, item_id, count],
      function(err) {
        if (err) reject(err);
        else resolve();
      }
    );
  });

  try {
    await updatePromise;
    
    // Clean up items with count <= 0
    await new Promise((resolve) => {
      db.run('DELETE FROM cart_items WHERE count <= 0', () => resolve());
    });

    ctx.status = 200;
  } catch (err) {
    ctx.status = 500;
    ctx.body = { error: 'Internal Server Error' };
  }
});

// POST /retrieve_cart
router.post('/retrieve_cart', async (ctx) => {
  const { cart_id } = ctx.request.body;

  if (!cart_id) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid request' };
    return;
  }

  const cartExists = await new Promise((resolve) => {
    db.get('SELECT 1 FROM carts WHERE cart_id = ?', [cart_id], (err, row) => {
      resolve(row);
    });
  });

  if (!cartExists) {
    ctx.status = 404;
    ctx.body = { error: 'Cart not found' };
    return;
  }

  const items = await new Promise((resolve, reject) => {
    db.all('SELECT item_id, count FROM cart_items WHERE cart_id = ?', [cart_id], (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });

  ctx.status = 200;
  ctx.body = { items };
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});