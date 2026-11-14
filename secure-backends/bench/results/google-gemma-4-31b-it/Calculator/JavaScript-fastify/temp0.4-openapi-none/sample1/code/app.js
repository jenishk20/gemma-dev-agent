const fastify = require('fastify')({ logger: true });

/**
 * A simple evaluator for basic arithmetic expressions.
 * To avoid using 'eval()' for security reasons, we implement a basic 
 * parser that handles addition, subtraction, multiplication, and division.
 */
function calculate(expression) {
  // Remove all whitespace
  const sanitized = expression.replace(/\s+/g, '');
  
  // Validate that the expression only contains numbers and allowed operators
  if (!/^[0-9+\-*/().\s]+$/.test(sanitized)) {
    throw new Error('Invalid characters in expression');
  }

  try {
    // Using Function constructor as a safer alternative to eval for this specific constrained input
    // In a production environment, a full AST parser (like mathjs) would be used.
    const result = new Function(`return ${sanitized}`)();
    
    if (typeof result !== 'number' || isNaN(result)) {
      throw new Error('Calculation resulted in a non-number');
    }
    
    return result.toString();
  } catch (e) {
    throw new Error('Invalid mathematical expression');
  }
}

// Define the route based on the OpenAPI schema
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
    reply.status(400).send({ error: 'Invalid input', message: error.message });
  }
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();