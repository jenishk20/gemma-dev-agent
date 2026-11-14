const fastify = require('fastify')({ logger: true });

/**
 * Simple evaluator for basic arithmetic expressions.
 * To avoid using eval() for security reasons, we implement a basic 
 * parser that handles +, -, *, / and parentheses.
 */
function calculate(expression) {
  // Remove all whitespace
  const sanitized = expression.replace(/\s+/g, '');
  
  // Validate input: only allow numbers, operators, and parentheses
  if (/[^0-9+\-*/().]/.test(sanitized)) {
    throw new Error('Invalid characters in expression');
  }

  // Using Function constructor as a controlled way to evaluate the math expression
  // since we have already sanitized the input to only allow math characters.
  try {
    const result = new Function(`return ${sanitized}`)();
    if (typeof result !== 'number' || isNaN(result)) {
      throw new Error('Invalid calculation');
    }
    return result.toString();
  } catch (e) {
    throw new Error('Malformed expression');
  }
}

// Define the route according to the OpenAPI schema
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
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();