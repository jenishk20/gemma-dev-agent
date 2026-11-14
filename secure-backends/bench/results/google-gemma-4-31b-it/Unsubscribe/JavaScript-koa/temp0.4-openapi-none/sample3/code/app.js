const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');

const app = new Koa();
const router = new Router();

/**
 * Helper to extract email from raw MIME text.
 * Looks for the "From:" header.
 */
function extractEmail(rawText) {
    const fromMatch = rawText.match(/^From:\s*.*<(.+?)>/m) || rawText.match(/^From:\s*([^\s\r\n]+)/m);
    return fromMatch ? fromMatch[1] : null;
}

/**
 * Helper to determine if the text contains unsubscribe keywords.
 */
function shouldUnsubscribe(rawText) {
    const keywords = ["unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"];
    const lowerText = rawText.toLowerCase();
    return keywords.some(keyword => lowerText.includes(keyword));
}

router.post('/decideUnsubscribe', async (ctx) => {
    // The OpenAPI spec defines requestBody as text/plain.
    // koa-bodyparser handles JSON and form-data. For raw text, we read the request body.
    
    let rawBody = '';
    for await (const chunk of ctx.req) {
        rawBody += chunk;
    }

    if (!rawBody) {
        ctx.throw(400, 'Empty request body');
    }

    const email = extractEmail(rawBody);
    const unsubscribe = shouldUnsubscribe(rawBody);

    ctx.set('Content-Type', 'application/json');
    ctx.body = {
        email: email || "unknown",
        unsubscribe: unsubscribe
    };
});

// Use bodyparser for general compatibility, though we read raw stream for text/plain
app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`Server running on http://${HOST}:${PORT}`);
});