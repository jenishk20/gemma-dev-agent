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
    const fromMatch = rawText.match(/^From:\s*.*<([^>]+)>/m) || rawText.match(/^From:\s*([^\s\r\n]+)/m);
    return fromMatch ? fromMatch[1] : null;
}

/**
 * Helper to determine if the text contains unsubscribe keywords.
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

// Custom middleware to handle text/plain request bodies since koa-bodyparser 
// primarily targets JSON/Form data.
async function textBodyParser(ctx, next) {
    if (ctx.request.body && typeof ctx.request.body === 'object' && ctx.request.header['content-type'] === 'text/plain') {
        // koa-bodyparser might have already tried to parse it. 
        // If it's empty or not a string, we read the raw stream.
    }
    
    if (ctx.request.header['content-type'] === 'text/plain') {
        let body = '';
        for await (const chunk of ctx.req) {
            body += chunk;
        }
        ctx.request.body = body;
    }
    await next();
}

router.post('/decideUnsubscribe', async (ctx) => {
    const rawEmail = ctx.request.body;

    if (!rawEmail || typeof rawEmail !== 'string') {
        ctx.status = 400;
        ctx.body = { error: "Invalid request body. Expected text/plain." };
        return;
    }

    const email = extractEmail(rawEmail);
    const unsubscribe = shouldUnsubscribe(rawEmail);

    ctx.status = 200;
    ctx.body = {
        email: email || "unknown",
        unsubscribe: unsubscribe
    };
});

app.use(textBodyParser);
app.use(bodyParser());
app.use(router.routes());
app.use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});