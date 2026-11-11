const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');

const app = new Koa();
const router = new Router();

/**
 * Simple evaluator for basic arithmetic expressions.
 * Supports +, -, *, / and parentheses.
 * Uses a basic recursive descent approach to avoid using eval() for security.
 */
function evaluateExpression(str) {
    // Remove whitespace
    str = str.replace(/\s+/g, '');
    
    let pos = 0;

    function parseExpression() {
        let node = parseTerm();
        while (pos < str.length && (str[pos] === '+' || str[pos] === '-')) {
            const op = str[pos++];
            const right = parseTerm();
            node = op === '+' ? node + right : node - right;
        }
        return node;
    }

    function parseTerm() {
        let node = parseFactor();
        while (pos < str.length && (str[pos] === '*' || str[pos] === '/')) {
            const op = str[pos++];
            const right = parseFactor();
            node = op === '*' ? node * right : node / right;
        }
        return node;
    }

    function parseFactor() {
        if (str[pos] === '(') {
            pos++; // skip (
            const result = parseExpression();
            pos++; // skip )
            return result;
        }
        
        let start = pos;
        while (pos < str.length && /[0-9.]/.test(str[pos])) {
            pos++;
        }
        const num = parseFloat(str.substring(start, pos));
        if (isNaN(num)) throw new Error("Invalid number");
        return num;
    }

    const result = parseExpression();
    if (pos !== str.length) throw new Error("Unexpected characters");
    return result;
}

router.post('/calculator', async (ctx) => {
    const body = ctx.request.body;

    if (!body || typeof body.expression !== 'string') {
        ctx.status = 400;
        ctx.body = { error: "Invalid input: expression is required and must be a string" };
        return;
    }

    try {
        const result = evaluateExpression(body.expression);
        ctx.status = 200;
        ctx.body = { result: result.toString() };
    } catch (err) {
        ctx.status = 400;
        ctx.body = { error: "Invalid arithmetic expression" };
    }
});

app.use(bodyParser());
app.use(router.routes());
app.use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});