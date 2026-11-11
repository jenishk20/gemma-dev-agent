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

  try {
    const now = new Date().toISOString();
    
    // Upsert: Insert new service or update existing one's token and timestamp
    const sql = `
      INSERT INTO services (serviceId, token, lastNotification) 
      VALUES (?, ?, ?) 
      ON CONFLICT(serviceId) DO UPDATE SET 
        token = excluded.token, 
        lastNotification = excluded.lastNotification
    `;
    
    db.run(sql, [serviceId, token, now], function(err) {
      if (err) {
        ctx.status = 500;
        ctx.body = { error: 'Internal server error' };
      } else {
        ctx.status = 200;
        ctx.body = { message: 'Heartbeat registered successfully.' };
      }
    });
  } catch (error) {
    ctx.status = 500;
    ctx.body = { error: 'Internal server error' };
  }
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

  try {
    const sql = `SELECT serviceId, lastNotification FROM services WHERE token = ?`;
    
    db.all(sql, [token], (err, rows) => {
      if (err) {
        ctx.status = 500;
        ctx.body = { error: 'Internal server error' };
      } else {
        ctx.status = 200;
        ctx.body = rows;
      }
    });
  } catch (error) {
    ctx.status = 500;
    ctx.body = { error: 'Internal server error' };
  }
});

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Service Monitoring API running on http://${HOST}:${PORT}`);
});