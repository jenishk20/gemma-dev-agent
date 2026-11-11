const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = new Koa();
const router = new Router();
const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS associations (
      card_number TEXT,
      phone_number TEXT,
      PRIMARY KEY (card_number, phone_number)
    )
  `);
});

// Middleware
app.use(bodyParser());

// POST /associate_card
router.post('/associate_card', async (ctx) => {
  const { credit_card, phone } = ctx.request.body;

  if (!credit_card || !phone) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid request: credit_card and phone are required' };
    return;
  }

  const stmt = db.prepare('INSERT OR IGNORE INTO associations (card_number, phone_number) VALUES (?, ?)');
  
  stmt.run(credit_card, phone, function(err) {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Internal server error' };
    } else {
      ctx.status = 201;
    }
  });
  
  // Since sqlite3 is callback based, we need to handle the response carefully.
  // In a real production app, we'd wrap this in a Promise.
  // For this implementation, we'll wrap the logic in a Promise to work with Koa's async nature.
});

// Redefining the routes using Promises for better Koa integration
router.post('/associate_card', async (ctx) => {
  const { credit_card, phone } = ctx.request.body;

  if (!credit_card || !phone) {
    ctx.status = 400;
    return;
  }

  try {
    await new Promise((resolve, reject) => {
      db.run('INSERT OR IGNORE INTO associations (card_number, phone_number) VALUES (?, ?)', [credit_card, phone], function(err) {
        if (err) reject(err);
        else resolve();
      });
    });
    ctx.status = 201;
  } catch (e) {
    ctx.status = 500;
  }
});

// POST /retrieve_cards
router.post('/retrieve_cards', async (ctx) => {
  const { phone_numbers } = ctx.request.body;

  if (!phone_numbers || !Array.isArray(phone_numbers) || phone_numbers.length === 0) {
    ctx.status = 400;
    return;
  }

  try {
    const cards = await new Promise((resolve, reject) => {
      // We need cards that are associated with ALL provided phone numbers.
      // We group by card_number and filter those where the count of distinct phone numbers matches the input array length.
      const placeholders = phone_numbers.map(() => '?').join(',');
      const query = `
        SELECT card_number 
        FROM associations 
        WHERE phone_number IN (${placeholders}) 
        GROUP BY card_number 
        HAVING COUNT(DISTINCT phone_number) = ?
      `;
      
      db.all(query, [...phone_numbers, phone_numbers.length], (err, rows) => {
        if (err) reject(err);
        else resolve(rows.map(row => row.card_number));
      });
    });

    if (cards.length === 0) {
      ctx.status = 404;
      ctx.body = { card_numbers: [] };
    } else {
      ctx.status = 200;
      ctx.body = { card_numbers: cards };
    }
  } catch (e) {
    ctx.status = 500;
  }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});