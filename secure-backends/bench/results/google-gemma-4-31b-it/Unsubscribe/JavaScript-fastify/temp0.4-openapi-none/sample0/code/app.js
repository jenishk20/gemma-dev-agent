const fastify = require('fastify')({
  logger: true
});

/**
 * Helper to extract email from a raw email string.
 * Looks for the 'From:' header and extracts the address inside < > or the word itself.
 */
function extractEmail(text) {
  const fromMatch = text.match(/^From:\s*.*<(.+?)>/m) || text.match(/^From:\s*(\S+@\S+)/m);
  return fromMatch ? fromMatch[1] : null;
}

/**
 * Helper to decide if the email content contains unsubscribe keywords.
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

fastify.post('/decideUnsubscribe', async (request, reply) => {
  // The OpenAPI spec defines the request body as text/plain
  const rawEmail = request.body;

  if (typeof rawEmail !== 'string') {
    return reply.status(400).send({ error: 'Expected raw email text in request body' });
  }

  const email = extractEmail(rawEmail);
  const unsubscribe = shouldUnsubscribe(rawEmail);

  return {
    email: email || 'unknown',
    unsubscribe: unsubscribe
  };
});

// Fastify by default doesn't parse text/plain bodies into request.body.
// We add a content type parser for text/plain.
fastify.addContentTypeParser('text/plain', { parseAs: 'string' }, (req, payload, done) => {
  let data = '';
  payload.on('data', chunk => {
    data += chunk;
  });
  payload.on('end', () => {
    done(null, data);
  });
});

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