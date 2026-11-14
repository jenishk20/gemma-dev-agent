const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');

const app = new Koa();
const router = new Router();

/**
 * Simple evaluator for arithmetic expressions.
 * To avoid using 'eval()' which is a security risk, 
 * we implement a basic parser or use a controlled Function constructor.
 * Since the requirements are for a simple calculator based on the schema,
 * we will use a Function constructor restricted to math operations.
 */
function calculate(expression) {
    // Sanitize input: allow only numbers, operators (+, -, *, /, .), spaces, and parentheses
    const sanitizedExpression = expression.replace(/[^-+*/0-9.()\s]/g, '');
    
    if (sanitizedExpression !== expression) {
        throw new Error('Invalid characters in expression');
    }

    try {
        // Use Function constructor as a safer alternative to eval for simple math
        const result = new Function(`return ${sanitizedExpression}`)();
        if (typeof result !== 'number' || isNaN(result)) {
            throw new Error('Invalid calculation result');
        }
        return result.toString();
    } catch (e) {
        throw new Error('Malformed expression');
    }
}

router.post('/calculator', async (ctx) => {
    const body = ctx.request.body;

    if (!body || typeof body.expression !== 'string') {
        ctx.status = 400;
        ctx.body = { error: 'Invalid input: expression is required and must be a string' };
        return;
    }

    try {
        const result = calculate(body.expression);
        ctx.status = 200;
        ctx.body = { result: result };
    } catch (err) {
        ctx.status = 400;
        ctx.body = { error: err.message };
    }
});

app.use(bodyParser());
app.use(router.routes());
app.use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});