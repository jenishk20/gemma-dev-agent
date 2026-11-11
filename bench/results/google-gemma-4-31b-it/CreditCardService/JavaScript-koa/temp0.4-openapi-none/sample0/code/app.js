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

app.use(bodyParser());

/**
 * POST /associate_card
 * Create a new association of a credit card number with a phone number.
 */
router.post('/associate_card', async (ctx) => {
  const { credit_card, phone } = ctx.request.body;

  if (!credit_card || !phone) {
    ctx.status = 400;
    ctx.body = { error: 'Missing credit_card or phone' };
    return;
  }

  const stmt = db.prepare('INSERT OR IGNORE INTO associations (card_number, phone_number) VALUES (?, ?)');
  
  try {
    await new Promise((resolve, reject) => {
      stmt.run(credit_card, phone, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
    ctx.status = 201;
  } catch (err) {
    ctx.status = 400;
    ctx.body = { error: 'Failed to create association' };
  } finally {
    stmt.finalize();
  }
});

/**
 * POST /retrieve_cards
 * Retrieve cards associated with all given phone numbers.
 */
router.post('/retrieve_cards', async (ctx) => {
  const { phone_numbers } = ctx.request.body;

  if (!phone_numbers || !Array.isArray(phone_numbers) || phone_numbers.length === 0) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid or missing phone_numbers array' };
    return;
  }

  // To find cards associated with ALL provided phone numbers, 
  // we group by card_number and filter for those where the count of distinct 
  // phone numbers matches the length of the input array.
  const placeholders = phone_numbers.map(() => '?').join(',');
  const query = `
    SELECT card_number 
    FROM associations 
    WHERE phone_number IN (${placeholders}) 
    GROUP BY card_number 
    HAVING COUNT(DISTINCT phone_number) = ?
  `;

  try {
    const results = await new Promise((resolve, reject) => {
      db.all(query, [...phone_numbers, phone_numbers.length], (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });

    const card_numbers = results.map(row => row.card_number);
    
    if (card_numbers.length === 0) {
      ctx.status = 404;
      ctx.body = { message: 'No cards found associated with all provided numbers' };
    } else {
      ctx.status = 200;
      ctx.body = { card_numbers };
    }
  } catch (err) {
    ctx.status = 400;
    ctx.body = { error: 'Database query error' };
  }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});