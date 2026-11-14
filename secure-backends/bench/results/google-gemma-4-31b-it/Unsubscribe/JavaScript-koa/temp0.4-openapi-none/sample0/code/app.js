const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');

const app = new Koa();
const router = new Router();

/**
 * Helper to extract email from raw email text.
 * Looks for the 'From:' header pattern.
 */
function extractEmail(rawText) {
  const fromMatch = rawText.match(/^From:.*<(.+?)>/m) || rawText.match(/^From:\s*([^\s\r\n]+@[^\s\r\n]+)/m);
  return fromMatch ? fromMatch[1] : null;
}

/**
 * Helper to determine if the email content suggests an unsubscribe request.
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

router.post('/decideUnsubscribe', async (ctx) => {
  // The OpenAPI schema specifies text/plain. 
  // koa-bodyparser handles raw bodies if configured, but for text/plain 
  // we can access the raw body via ctx.request.body if it's a string 
  // or we can read the request stream.
  
  let rawEmail = '';
  
  // If koa-bodyparser processed it as a string
  if (typeof ctx.request.body === 'string') {
    rawEmail = ctx.request.body;
  } else if (ctx.request.body && ctx.request.body.text) {
    rawEmail = ctx.request.body.text;
  } else {
    // Fallback: read the raw request body manually if bodyparser didn't catch it
    // because it's text/plain and not application/json
    const buffers = [];
    for await (const chunk of ctx.req) {
      buffers.push(chunk);
    }
    rawEmail = Buffer.concat(buffers).toString('utf8');
  }

  if (!rawEmail) {
    ctx.throw(400, 'Empty request body');
  }

  const email = extractEmail(rawEmail);
  const unsubscribe = shouldUnsubscribe(rawEmail);

  ctx.set('Content-Type', 'application/json');
  ctx.body = {
    email: email || "unknown",
    unsubscribe: unsubscribe
  };
});

// Use bodyparser to handle potential JSON or form data, 
// though the spec asks for text/plain.
app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});