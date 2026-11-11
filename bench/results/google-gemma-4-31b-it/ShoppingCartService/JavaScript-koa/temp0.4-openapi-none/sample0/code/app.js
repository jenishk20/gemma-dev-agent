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
  
  const query = `INSERT INTO carts (cart_id) VALUES (?)`;
  db.run(query, [cart_id], function(err) {
    if (err) {
      ctx.throw(500, 'Database error');
    }
    ctx.status = 201;
    ctx.body = { cart_id };
  });
});

// POST /add_to_cart
router.post('/add_to_cart', async (ctx) => {
  const { cart_id, item_id, count } = ctx.request.body;

  if (!cart_id || item_id === undefined || count === undefined) {
    ctx.status = 400;
    ctx.body = 'Invalid request: missing required fields';
    return;
  }

  // Check if cart exists
  db.get(`SELECT cart_id FROM carts WHERE cart_id = ?`, [cart_id], (err, row) => {
    if (err) {
      ctx.throw(500, 'Database error');
    }
    if (!row) {
      ctx.status = 404;
      ctx.body = 'Cart not found';
      return;
    }

    // Update or Insert item count
    // SQLite UPSERT syntax (INSERT ... ON CONFLICT)
    const query = `
      INSERT INTO cart_items (cart_id, item_id, count) 
      VALUES (?, ?, ?) 
      ON CONFLICT(cart_id, item_id) DO UPDATE SET count = count + excluded.count
    `;
    
    db.run(query, [cart_id, item_id, count], function(err) {
      if (err) {
        ctx.throw(500, 'Database error');
      }
      
      // Clean up: remove items with count <= 0
      db.run(`DELETE FROM cart_items WHERE cart_id = ? AND item_id = ? AND count <= 0`, [cart_id, item_id]);
      
      ctx.status = 200;
      ctx.body = { message: 'Item updated successfully' };
    });
  });
});

// POST /retrieve_cart
router.post('/retrieve_cart', async (ctx) => {
  const { cart_id } = ctx.request.body;

  if (!cart_id) {
    ctx.status = 400;
    ctx.body = 'Invalid request: missing cart_id';
    return;
  }

  // Check if cart exists
  db.get(`SELECT cart_id FROM carts WHERE cart_id = ?`, [cart_id], (err, row) => {
    if (err) {
      ctx.throw(500, 'Database error');
    }
    if (!row) {
      ctx.status = 404;
      ctx.body = 'Cart not found';
      return;
    }

    const query = `SELECT item_id, count FROM cart_items WHERE cart_id = ?`;
    db.all(query, [cart_id], (err, rows) => {
      if (err) {
        ctx.throw(500, 'Database error');
      }
      ctx.status = 200;
      ctx.body = { items: rows };
    });
  });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Shopping Cart Service running on port 5000');
});