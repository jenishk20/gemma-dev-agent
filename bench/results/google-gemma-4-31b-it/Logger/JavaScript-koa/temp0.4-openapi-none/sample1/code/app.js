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
 * Log a message to the server.
 */
router.post('/log', async (ctx) => {
  const { message } = ctx.request.body;

  if (typeof message !== 'string') {
    ctx.throw(400, 'Invalid request: "message" field is required and must be a string.');
  }

  // Append the message to the file with a newline
  fs.appendFileSync(LOG_FILE, message + '\n', 'utf8');

  ctx.status = 200;
  ctx.body = 'Log message successful';
});

/**
 * GET /logs
 * Retrieve all logged messages.
 */
router.get('/logs', async (ctx) => {
  try {
    if (!fs.existsSync(LOG_FILE)) {
      ctx.body = '';
      return;
    }
    const data = fs.readFileSync(LOG_FILE, 'utf8');
    ctx.type = 'text/plain';
    ctx.body = data;
  } catch (err) {
    ctx.throw(500, 'Error reading logs file');
  }
});

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Logging service running at http://${HOST}:${PORT}`);
});