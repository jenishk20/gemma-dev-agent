const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();
const LOG_FILE = path.join(__dirname, 'logs.txt');

// Middleware to parse JSON bodies
app.use(bodyParser());

/**
 * POST /log
 * Logs a message to the server.
 */
router.post('/log', async (ctx) => {
  const body = ctx.request.body;

  if (!body || typeof body.message !== 'string') {
    ctx.throw(400, 'Invalid request body: "message" string is required');
  }

  try {
    // Append the message to logs.txt with a newline
    fs.appendFileSync(LOG_FILE, body.message + '\n', 'utf8');
    ctx.status = 200;
    ctx.body = 'Log message successful';
  } catch (err) {
    ctx.throw(500, 'Internal server error writing to log file');
  }
});

/**
 * GET /logs
 * Retrieve all logged messages.
 */
router.get('/logs', async (ctx) => {
  try {
    if (!fs.existsSync(LOG_FILE)) {
      ctx.status = 200;
      ctx.body = '';
      return;
    }

    const logs = fs.readFileSync(LOG_FILE, 'utf8');
    ctx.status = 200;
    ctx.type = 'text/plain';
    ctx.body = logs;
  } catch (err) {
    ctx.throw(500, 'Internal server error reading log file');
  }
});

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`LoggingAPI server running at http://${HOST}:${PORT}`);
});