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

  const query = `
    INSERT INTO services (serviceId, token, lastNotification) 
    VALUES (?, ?, CURRENT_TIMESTAMP) 
    ON CONFLICT(serviceId) DO UPDATE SET 
      token = excluded.token, 
      lastNotification = CURRENT_TIMESTAMP
  `;

  db.run(query, [serviceId, token], (err) => {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Internal server error' };
      return;
    }
    ctx.status = 200;
    ctx.body = { message: 'Heartbeat registered successfully.' };
  });
});

/**
 * POST /services
 * Get overview of registered services matching the provided token
 */
router.post('/services', async (ctx) => {
  const { token } = ctx.request.body;

  if (!token) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid request payload. token is required.' };
    return;
  }

  const query = `SELECT serviceId, lastNotification FROM services WHERE token = ?`;

  db.all(query, [token], (err, rows) => {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Internal server error' };
      return;
    }

    // Format the output to match the OpenAPI schema
    const response = rows.map(row => ({
      serviceId: row.serviceId,
      lastNotification: row.lastNotification
    }));

    ctx.status = 200;
    ctx.body = response;
  });
});

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Service Monitoring API running on http://${HOST}:${PORT}`);
});