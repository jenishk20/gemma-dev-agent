const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');

const app = new Koa();
const router = new Router();

/**
 * Extracts the email address from the raw email text.
 * Looks for the "From:" header pattern.
 */
function extractEmail(text) {
  const fromMatch = text.match(/^From:.*<(.+?)>/m) || text.match(/^From:\s*([^\s\r\n]+)/m);
  return fromMatch ? fromMatch[1] : null;
}

/**
 * Decides if the email content indicates a request to unsubscribe.
 */
function shouldUnsubscribe(text) {
  const keywords = [
    "unsubscribe",
    "remove me",
    "deregister me",
    "stop sending me",
    "delete me"
  ];
  const lowerText = text.toLowerCase();
  return keywords.some(keyword => lowerText.includes(keyword));
}

router.post('/decideUnsubscribe', async (ctx) => {
  // The OpenAPI spec specifies text/plain. 
  // koa-bodyparser handles text/plain if configured, 
  // but we can also access the raw body if needed.
  const rawBody = ctx.request.body;

  if (typeof rawBody !== 'string') {
    ctx.throw(400, 'Expected raw text/plain body');
  }

  const email = extractEmail(rawBody);
  const unsubscribe = shouldUnsubscribe(rawBody);

  ctx.set('Content-Type', 'application/json');
  ctx.body = {
    email: email || "unknown",
    unsubscribe: unsubscribe
  };
});

// Configure bodyparser to handle text/plain
app.use(bodyParser({
  enableTypes: ['json', 'text'],
}));

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Server running on http://${HOST}:${PORT}`);
});