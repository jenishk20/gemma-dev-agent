const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();
const LOG_FILE = path.join(__dirname, 'logs.txt');

app.use(bodyParser());

// POST /log - Log a message
router.post('/log', async (ctx) => {
  const { message } = ctx.request.body;

  if (typeof message !== 'string') {
    ctx.throw(400, 'Invalid request body: message must be a string');
  }

  // Append the message to the file followed by a newline
  fs.appendFileSync(LOG_FILE, message + '\n', 'utf8');
  
  ctx.status = 200;
  ctx.body = 'Log message successful';
});

// GET /logs - Retrieve all logs
router.get('/logs', async (ctx) => {
  try {
    // Read the entire file content
    if (!fs.existsSync(LOG_FILE)) {
      ctx.body = '';
      return;
    }
    const data = fs.readFileSync(LOG_FILE, 'utf8');
    ctx.type = 'text/plain';
    ctx.body = data;
  } catch (err) {
    ctx.throw(500, 'Error retrieving logs');
  }
});

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`LoggingAPI server running at http://${HOST}:${PORT}`);
});