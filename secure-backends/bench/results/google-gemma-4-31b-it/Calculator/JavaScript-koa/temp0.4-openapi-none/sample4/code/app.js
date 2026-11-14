const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');

const app = new Koa();
const router = new Router();

app.use(bodyParser());

/**
 * Safely evaluates a mathematical expression.
 * Since we are restricted to the provided packages and standard library,
 * we implement a basic parser or use a controlled Function constructor.
 * To prevent arbitrary code execution, we sanitize the input to only allow 
 * numbers, basic operators, and parentheses.
 */
function calculate(expression) {
    // Remove all whitespace
    const sanitized = expression.replace(/\s+/g, '');
    
    // Regex to allow only: digits, ., +, -, *, /, (, )
    // This prevents RCE by ensuring no alphabetic characters or dangerous symbols are passed to the evaluator
    if (!/^[0-9.+\-*/() ]*$/.test(sanitized)) {
        throw new Error('Invalid characters in expression');
    }

    try {
        // Use Function constructor as a sandbox-lite for simple math
        // This is safe here because of the strict regex validation above
        const result = new Function(`return ${sanitized}`)();
        
        if (typeof result !== 'number' || isNaN(result)) {
            throw new Error('Calculation resulted in an invalid number');
        }
        
        return result.toString();
    } catch (e) {
        throw new Error('Invalid mathematical expression');
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
        ctx.body = { result: result };
    } catch (error) {
        ctx.status = 400;
        ctx.body = { error: error.message };
    }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});