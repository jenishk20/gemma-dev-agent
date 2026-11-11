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
    CREATE TABLE IF NOT EXISTS card_phone_association (
      credit_card TEXT,
      phone TEXT,
      PRIMARY KEY (credit_card, phone)
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
    ctx.throw(400, 'Invalid request: credit_card and phone are required');
  }

  const stmt = db.prepare('INSERT OR IGNORE INTO card_phone_association (credit_card, phone) VALUES (?, ?)');
  
  stmt.run(credit_card, phone, function(err) {
    if (err) {
      ctx.throw(500, 'Database error');
    }
    ctx.status = 201;
  });
  
  // Since sqlite3 is callback based, we wrap the logic to ensure Koa handles the response
  await new Promise((resolve) => {
    stmt.finalize(() => resolve());
  });
});

/**
 * POST /retrieve_cards
 * Retrieve cards associated with all given phone numbers.
 */
router.post('/retrieve_cards', async (ctx) => {
  const { phone_numbers } = ctx.request.body;

  if (!phone_numbers || !Array.isArray(phone_numbers) || phone_numbers.length === 0) {
    ctx.throw(400, 'Invalid request: phone_numbers must be a non-empty array');
  }

  // To find cards associated with ALL given phone numbers:
  // We group by credit_card and filter for those where the count of distinct phone numbers 
  // matching the input list equals the size of the input list.
  const placeholders = phone_numbers.map(() => '?').join(',');
  const query = `
    SELECT credit_card 
    FROM card_phone_association 
    WHERE phone IN (${placeholders}) 
    GROUP BY credit_card 
    HAVING COUNT(DISTINCT phone) = ?
  `;

  const params = [...phone_numbers, phone_numbers.length];

  db.all(query, params, (err, rows) => {
    if (err) {
      ctx.throw(500, 'Database error');
    }

    if (!rows || rows.length === 0) {
      ctx.status = 404;
      ctx.body = { card_numbers: [] };
      return;
    }

    const card_numbers = rows.map(row => row.credit_card);
    ctx.status = 200;
    ctx.body = { card_numbers };
  });

  // Wrap in promise to handle async flow in Koa
  await new Promise((resolve) => {
    // We use a small timeout or a custom wrapper if needed, 
    // but for this simple logic, the callback handles the response.
    // To properly integrate with Koa's async middleware, we'd usually use a promisified db.
    resolve();
  });
});

// Custom wrapper to handle the sqlite3 callback pattern within Koa's async handlers
// Since the above uses callbacks, we need to ensure the response is sent.
// Let's rewrite the handlers using Promises for reliability.

const dbQuery = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
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

// Overwriting the routes with Promise-based logic
router.post('/associate_card', async (ctx) => {
  const { credit_card, phone } = ctx.request.body;
  if (!credit_card || !phone) {
    ctx.status = 400;
    return;
  }
  try {
    await dbRun('INSERT OR IGNORE INTO card_phone_association (credit_card, phone) VALUES (?, ?)', [credit_card, phone]);
    ctx.status = 201;
  } catch (e) {
    ctx.status = 500;
  }
});

router.post('/retrieve_cards', async (ctx) => {
  const { phone_numbers } = ctx.request.body;
  if (!phone_numbers || !Array.isArray(phone_numbers) || phone_numbers.length === 0) {
    ctx.status = 400;
    return;
  }

  const placeholders = phone_numbers.map(() => '?').join(',');
  const query = `SELECT credit_card FROM card_phone_association WHERE phone IN (${placeholders}) GROUP BY credit_card HAVING COUNT(DISTINCT phone) = ?`;
  
  try {
    const rows = await dbQuery(query, [...phone_numbers, phone_numbers.length]);
    if (rows.length === 0) {
      ctx.status = 404;
      ctx.body = { card_numbers: [] };
    } else {
      ctx.status = 200;
      ctx.body = { card_numbers: rows.map(r => r.credit_card) };
    }
  } catch (e) {
    ctx.status = 500;
  }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});