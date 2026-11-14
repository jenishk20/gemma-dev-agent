const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');

const app = new Koa();
const router = new Router();

/**
 * Helper to extract email from the "From:" header of a raw email string.
 * Matches patterns like "Name <email@domain.com>" or just "email@domain.com"
 */
function extractEmail(rawText) {
  const fromMatch = rawText.match(/^From:\s*.*<(.+?)>/m) || rawText.match(/^From:\s*([^\s\r\n]+@[^\s\r\n]+)/m);
  return fromMatch ? fromMatch[1] : null;
}

/**
 * Helper to decide if the email content contains unsubscribe keywords.
 */
function shouldUnsubscribe(rawText) {
  const keywords = [
    "unsubscribe",
    "remove me",
    "deregister me",
    "stop sending me",
    "delete me"
  ];
  const lowerText = rawText.toLowerCase();
  return keywords.some(keyword => lowerText.includes(keyword));
}

// Middleware to handle raw text bodies since koa-bodyparser primarily targets JSON/URL-encoded
// We use a custom approach to read the raw request body for text/plain
app.use(async (ctx, next) => {
  if (ctx.request.headers['content-type'] === 'text/plain') {
    let body = '';
    for await (const chunk of ctx.req) {
      body += chunk;
    }
    ctx.request.body = body;
  }
  await next();
});

router.post('/decideUnsubscribe', async (ctx) => {
  const rawEmail = ctx.request.body;

  if (!rawEmail || typeof rawEmail !== 'string') {
    ctx.throw(400, 'Invalid request body. Expected text/plain email content.');
  }

  const email = extractEmail(rawEmail);
  const unsubscribe = shouldUnsubscribe(rawEmail);

  ctx.set('Content-Type', 'application/json');
  ctx.body = {
    email: email || "unknown",
    unsubscribe: unsubscribe
  };
});

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Server running on http://${HOST}:${PORT}`);
});