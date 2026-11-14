const fastify = require('fastify')({ 
  logger: false 
});

/**
 * Helper to extract the email address from the raw email text.
 * Looks for the "From:" header pattern.
 */
function extractEmail(text) {
  const fromMatch = text.match(/^From:.*<(.+?)>/m) || text.match(/^From:\s*([^\s\r\n]+)/m);
  return fromMatch ? fromMatch[1] : null;
}

/**
 * Helper to determine if the email content contains unsubscribe keywords.
 */
function shouldUnsubscribe(text) {
  const keywords = [
    "unsubscribe", 
    "remove me", 
    "deregister me", 
    "stop sending me", 
    "delete me"
  ];
  const lowerText = text.toLowerCase();
  return keywords.some(keyword => lowerText.includes(keyword));
}

// The endpoint implementation
fastify.post('/decideUnsubscribe', async (request, reply) => {
  // The OpenAPI spec defines the request body as text/plain
  const rawEmail = request.body;

  if (typeof rawEmail !== 'string') {
    return reply.status(400).send({ error: 'Expected raw email text in request body' });
  }

  const email = extractEmail(rawEmail);
  const unsubscribe = shouldUnsubscribe(rawEmail);

  return {
    email: email || "unknown",
    unsubscribe: unsubscribe
  };
});

// Fastify by default parses JSON. To handle text/plain as the body, 
// we add a content type parser.
fastify.addContentTypeParser('text/plain', { parseAs: 'string' }, (err, payload) => {
  if (err) throw err;
  payload; 
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ 
      port: 5000, 
      host: '0.0.0.0' 
    });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();