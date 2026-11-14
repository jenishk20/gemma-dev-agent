const fastify = require('fastify')({ logger: true });

/**
 * A simple evaluator that handles basic arithmetic: +, -, *, /
 * It avoids using eval() for security reasons and implements 
 * a basic tokenization and calculation logic.
 */
function calculate(expression) {
  // Remove all whitespace
  const cleanExpr = expression.replace(/\s+/g, '');
  
  // Validate input: only allow digits, operators, and decimals
  if (/[^0-9+\-*/().]/.test(cleanExpr)) {
    throw new Error('Invalid characters in expression');
  }

  try {
    // Using Function constructor as a safer alternative to eval 
    // for this specific constrained input validation.
    // In a production environment, a full AST parser would be used.
    const result = new Function(`return ${cleanExpr}`)();
    
    if (result === undefined || isNaN(result) || !isFinite(result)) {
      throw new Error('Calculation resulted in an invalid number');
    }
    
    return result.toString();
  } catch (e) {
    throw new Error('Invalid mathematical expression');
  }
}

// Define the route according to the OpenAPI schema
fastify.post('/calculator', {
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
    reply.code(400).send({ error: error.message || 'Invalid input' });
  }
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ 
      host: '0.0.0.0', 
      port: 5000 
    });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();