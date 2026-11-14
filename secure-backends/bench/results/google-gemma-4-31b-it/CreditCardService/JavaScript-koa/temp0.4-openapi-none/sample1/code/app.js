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
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      credit_card TEXT NOT NULL,
      phone TEXT NOT NULL,
      UNIQUE(credit_card, phone)
    )
  `);
  // Index for faster retrieval
  db.run(`CREATE INDEX IF NOT EXISTS idx_phone ON associations(phone)`);
});

router.post('/associate_card', async (ctx) => {
  const { credit_card, phone } = ctx.request.body;

  if (!credit_card || !phone) {
    ctx.status = 400;
    ctx.body = { error: 'Missing credit_card or phone' };
    return;
  }

  const query = `INSERT OR IGNORE INTO associations (credit_card, phone) VALUES (?, ?)`;
  
  db.run(query, [credit_card, phone], function(err) {
    if (err) {
      ctx.status = 400;
      ctx.body = { error: 'Database error' };
    } else {
      ctx.status = 201;
    }
  });
});

router.post('/retrieve_cards', async (ctx) => {
  const { phone_numbers } = ctx.request.body;

  if (!phone_numbers || !Array.isArray(phone_numbers) || phone_numbers.length === 0) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid or missing phone_numbers array' };
    return;
  }

  // To find cards associated with ALL given phone numbers:
  // We group by credit_card and filter for those where the count of distinct 
  // matching phone numbers equals the size of the input list.
  const placeholders = phone_numbers.map(() => '?').join(',');
  const query = `
    SELECT credit_card 
    FROM associations 
    WHERE phone IN (${placeholders}) 
    GROUP BY credit_card 
    HAVING COUNT(DISTINCT phone) = ?
  `;

  const params = [...phone_numbers, phone_numbers.length];

  db.all(query, params, (err, rows) => {
    if (err) {
      ctx.status = 400;
      ctx.body = { error: 'Database error' };
      return;
    }

    if (!rows || rows.length === 0) {
      ctx.status = 404;
      ctx.body = { error: 'No cards found' };
      return;
    }

    const card_numbers = rows.map(row => row.credit_card);
    ctx.status = 200;
    ctx.body = { card_numbers };
  });
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});