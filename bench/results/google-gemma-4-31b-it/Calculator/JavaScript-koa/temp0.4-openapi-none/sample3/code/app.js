const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');

const app = new Koa();
const router = new Router();

app.use(bodyParser());

/**
 * Safely evaluates a mathematical expression.
 * To avoid using eval() on untrusted input, we implement a basic 
 * parser or a restricted evaluation. For the purpose of this 
 * exercise and the provided schema, we will use a Function constructor 
 * which is slightly safer than eval but still powerful. 
 * We sanitize the input to only allow numbers, operators, and parentheses.
 */
function calculate(expression) {
    // Sanitize input: allow only digits, ., +, -, *, /, (, ), and spaces
    const sanitized = expression.replace(/[^0-9.\+\-\*\/\(\)\s]/g, '');
    
    try {
        // Using Function constructor to evaluate the math expression
        const result = new Function(`return (${sanitized})`)();
        if (isNaN(result) || !isFinite(result)) {
            throw new Error('Invalid calculation result');
        }
        return String(result);
    } catch (e) {
        throw new Error('Invalid expression');
    }
}

router.post('/calculator', async (ctx) => {
    const { expression } = ctx.request.body;

    if (!expression || typeof expression !== 'string') {
        ctx.status = 400;
        ctx.body = { error: 'Invalid input: expression is required and must be a string' };
        return;
    }

    try {
        const result = calculate(expression);
        ctx.status = 200;
        ctx.body = { result };
    } catch (error) {
        ctx.status = 400;
        ctx.body = { error: 'Invalid input: could not evaluate expression' };
    }
});

app.use(router.routes()).use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
    console.log(`Server running on http://${HOST}:${PORT}`);
});