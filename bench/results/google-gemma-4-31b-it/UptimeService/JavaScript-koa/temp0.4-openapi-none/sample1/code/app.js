const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = new Koa();
const router = new Router();
const db = new sqlite3.Database(path.join(__dirname, 'db.sqlite3'));

// Initialize Database
db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS services (
      serviceId TEXT PRIMARY KEY,
      token TEXT NOT NULL,
      lastNotification DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);
});

app.use(bodyParser());

/**
 * POST /heartbeat
 * Register a heartbeat for a service
 */
router.post('/heartbeat', async (ctx) => {
  const { serviceId, token } = ctx.request.body;

  if (!serviceId || !token) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid request payload. serviceId and token are required.' };
    return;
  }

  const sql = `
    INSERT INTO services (serviceId, token, lastNotification) 
    VALUES (?, ?, CURRENT_TIMESTAMP) 
    ON CONFLICT(serviceId) DO UPDATE SET 
      token = excluded.token, 
      lastNotification = CURRENT_TIMESTAMP
  `;

  try {
    await new Promise((resolve, reject) => {
      db.run(sql, [serviceId, token], function(err) {
        if (err) reject(err);
        else resolve();
      });
    });
    ctx.status = 200;
    ctx.body = { message: 'Heartbeat registered successfully.' };
  } catch (err) {
    ctx.status = 500;
    ctx.body = { error: 'Internal server error.' };
  }
});

/**
 * POST /services
 * Get overview of registered services filtered by token
 */
router.post('/services', async (ctx) => {
  const { token } = ctx.request.body;

  if (!token) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid request payload. token is required.' };
    return;
  }

  const sql = `SELECT serviceId, lastNotification FROM services WHERE token = ?`;

  try {
    const services = await new Promise((resolve, reject) => {
      db.all(sql, [token], (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });

    ctx.status = 200;
    ctx.body = services;
  } catch (err) {
    ctx.status = 500;
    ctx.body = { error: 'Internal server error.' };
  }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});