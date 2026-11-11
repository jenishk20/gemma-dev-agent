const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = new Koa();
const router = new Router();
const PORT = 5000;
const HOST = '0.0.0.0';

// Database initialization
const db = new sqlite3.Database(path.join(__dirname, 'db.sqlite3'));

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

  const now = new Date().toISOString();

  try {
    // Use UPSERT logic to update the timestamp and token for the given serviceId
    db.run(
      `INSERT INTO services (serviceId, token, lastNotification) 
       VALUES (?, ?, ?) 
       ON CONFLICT(serviceId) DO UPDATE SET 
       token = excluded.token, 
       lastNotification = excluded.lastNotification`,
      [serviceId, token, now],
      function(err) {
        if (err) {
          ctx.status = 500;
          ctx.body = { error: 'Internal server error' };
        } else {
          ctx.status = 200;
          ctx.body = { message: 'Heartbeat registered successfully.' };
        }
      }
    );
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
    ctx.body = { error: 'Token is required' };
    return;
  }

  try {
    db.all(
      `SELECT serviceId, lastNotification FROM services WHERE token = ?`,
      [token],
      (err, rows) => {
        if (err) {
          ctx.status = 500;
          ctx.body = { error: 'Internal server error' };
        } else {
          ctx.status = 200;
          ctx.body = rows;
        }
      }
    );
  } catch (error) {
    ctx.status = 500;
    ctx.body = { error: 'Internal server error' };
  }
});

// Wrap DB calls in promises to ensure Koa handles the async flow correctly 
// since sqlite3 is callback-based.
const wrapAsync = (fn) => {
  return async (ctx, next) => {
    try {
      await fn(ctx, next);
    } catch (err) {
      ctx.status = 500;
      ctx.body = { error: 'Internal server error' };
    }
  };
};

// Overriding the routes with a promise-based approach to prevent Koa from 
// sending responses before the DB callback executes.
router.post('/heartbeat', async (ctx) => {
  const { serviceId, token } = ctx.request.body;
  if (!serviceId || !token) {
    ctx.status = 400;
    return;
  }
  const now = new Date().toISOString();
  
  await new Promise((resolve, reject) => {
    db.run(
      `INSERT INTO services (serviceId, token, lastNotification) 
       VALUES (?, ?, ?) 
       ON CONFLICT(serviceId) DO UPDATE SET 
       token = excluded.token, 
       lastNotification = excluded.lastNotification`,
      [serviceId, token, now],
      function(err) {
        if (err) reject(err);
        else resolve();
      }
    );
  });
  ctx.status = 200;
});

router.post('/services', async (ctx) => {
  const { token } = ctx.request.body;
  if (!token) {
    ctx.status = 400;
    return;
  }

  const rows = await new Promise((resolve, reject) => {
    db.all(
      `SELECT serviceId, lastNotification FROM services WHERE token = ?`,
      [token],
      (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      }
    );
  });
  ctx.status = 200;
  ctx.body = rows;
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(PORT, HOST, () => {
  console.log(`Server running on http://${HOST}:${PORT}`);
});