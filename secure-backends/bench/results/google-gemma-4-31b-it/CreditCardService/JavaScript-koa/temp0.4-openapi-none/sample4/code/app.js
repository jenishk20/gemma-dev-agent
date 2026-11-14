const Koa = require('koa');
const bodyParser = require('koa-bodyparser');
const Router = require('koa-router');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = new Koa();
const router = new Router();
const db = new sqlite3.Database(path.join(__dirname, 'db.sqlite3'));

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

  const query = `INSERT OR IGNORE INTO associations (card_number, phone_number) VALUES (?, ?)`;
  
  db.run(query, [credit_card, phone], function(err) {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Database error' };
    } else {
      ctx.status = 201;
    }
  });
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

  // To find cards associated with ALL provided phone numbers:
  // We group by card_number and filter for those where the count of distinct 
  // matching phone numbers equals the size of the input list.
  const placeholders = phone_numbers.map(() => '?').join(',');
  const query = `
    SELECT card_number 
    FROM associations 
    WHERE phone_number IN (${placeholders}) 
    GROUP BY card_number 
    HAVING COUNT(DISTINCT phone_number) = ?
  `;

  const params = [...phone_numbers, phone_numbers.length];

  db.all(query, params, (err, rows) => {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Database error' };
      return;
    }

    const card_numbers = rows.map(row => row.card_number);
    
    if (card_numbers.length === 0) {
      ctx.status = 404;
      ctx.body = { message: 'No cards found associated with all provided numbers' };
    } else {
      ctx.status = 200;
      ctx.body = { card_numbers };
    }
  });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen({ port: 5000, host: '0.0.0.0' }, () => {
  console.log('Server running on http://0.0.0.0:5000');
});