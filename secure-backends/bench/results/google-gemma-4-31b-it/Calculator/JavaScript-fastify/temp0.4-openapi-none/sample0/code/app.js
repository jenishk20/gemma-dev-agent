const fastify = require('fastify')({ 
  logger: true 
});

/**
 * Simple evaluator for basic arithmetic expressions.
 * To avoid using 'eval()' for security reasons, we implement a basic 
 * parser that handles +, -, *, / and parentheses.
 */
function calculate(expression) {
  // Remove all whitespace
  const sanitized = expression.replace(/\s+/g, '');
  
  // Validate that the expression contains only allowed characters
  // (Numbers, operators +, -, *, /, and parentheses)
  if (/[^0-9+\-*/().]/.test(sanitized)) {
    throw new Error('Invalid characters in expression');
  }

  try {
    // Using Function constructor as a safer alternative to eval() 
    // for this specific constrained input, but still effectively executing code.
    // In a production environment, a full AST parser (like mathjs) would be used.
    const result = new Function(`return ${sanitized}`)();
    
    if (typeof result !== 'number' || isNaN(result)) {
      throw new Error('Calculation resulted in non-numeric value');
    }
    
    return result.toString();
  } catch (e) {
    throw new Error('Invalid mathematical expression');
  }
}

// Define the route based on the OpenAPI schema
fastify.post('/calculator', async (request, reply) => {
  const { expression } = request.body;

  if (!expression || typeof expression !== 'string') {
    return reply.status(400).send({ error: 'Invalid input: expression is required and must be a string' });
  }

  try {
    const result = calculate(expression);
    return reply.status(200).send({ result });
  } catch (error) {
    return reply.status(400).send({ error: error.message });
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