const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');

const app = new Koa();
const router = new Router();

/**
 * Safely evaluates a mathematical expression.
 * Since we are restricted to the provided packages and standard library,
 * and cannot use 'eval' blindly for security reasons, we implement 
 * a basic validation and evaluation logic.
 */
function calculate(expression) {
  // Remove all whitespace
  const sanitized = expression.replace(/\s+/g, '');
  
  // Validate that the expression contains only numbers, basic operators, and parentheses
  // This prevents arbitrary code execution via eval()
  if (!/^[\d\+\-\*\/\.\(\)]+$/.test(sanitized)) {
    throw new Error('Invalid characters in expression');
  }

  try {
    // Using Function constructor as a safer alternative to eval for simple math
    // though still cautious. In a production environment, a proper parser is preferred.
    const result = new Function(`return ${sanitized}`)();
    
    if (result === Infinity || result === -Infinity || isNaN(result)) {
      throw new Error('Calculation resulted in an invalid number');
    }
    
    return String(result);
  } catch (e) {
    throw new Error('Malformed expression');
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
  } catch (err) {
    ctx.status = 400;
    ctx.body = { error: err.message };
  }
});

app.use(bodyParser());
app.use(router.routes());
app.use(router.allowedMethods());

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Calculator server running at http://${HOST}:${PORT}`);
});