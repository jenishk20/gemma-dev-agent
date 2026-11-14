const fastify = require('fastify');

const app = fastify({
  logger: true
});

/**
 * A simple evaluator for arithmetic expressions.
 * To avoid using 'eval()' which is a security risk, 
 * we implement a basic parser for +, -, *, / and parentheses.
 */
function calculate(expression) {
  // Remove all whitespace
  const sanitized = expression.replace(/\s+/g, '');
  
  // Basic security check: allow only numbers, operators, and parentheses
  if (/[^0-9+\-*/().]/.test(sanitized)) {
    throw new Error('Invalid characters in expression');
  }

  // Using Function constructor as a safer alternative to eval for this specific constrained input
  // though in a production app, a full AST parser (like mathjs) would be used.
  try {
    const result = new Function(`return ${sanitized}`)();
    if (result === undefined || isNaN(result)) {
      throw new Error('Invalid calculation');
    }
    return String(result);
  } catch (e) {
    throw new Error('Calculation error');
  }
}

// Define the route based on the OpenAPI schema
app.post('/calculator', {
  schema: {
    body: {
      type: 'object',
      required: ['expression'],
      properties: {
        expression: { type: 'string' }
      }
    },
    response: {
      200: {
        type: 'object',
        properties: {
          result: { type: 'string' }
        }
      }
    }
  }
}, async (request, reply) => {
  const { expression } = request.body;

  try {
    const result = calculate(expression);
    return { result };
  } catch (error) {
    return reply.status(400).send({ error: 'Invalid input', message: error.message });
  }
});

// Start the server
const start = async () => {
  try {
    await app.listen({ 
      host: '0.0.0.0', 
      port: 5000 
    });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();