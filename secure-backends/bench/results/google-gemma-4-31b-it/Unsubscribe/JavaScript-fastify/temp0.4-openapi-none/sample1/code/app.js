const fastify = require('fastify')({ logger: true });

/**
 * Helper to extract the email address from the raw email text.
 * Looks for the 'From:' header pattern.
 */
function extractEmail(text) {
  const fromMatch = text.match(/^From:.*<(.+?)>/m) || text.match(/^From:\s*(\S+@\S+)/m);
  return fromMatch ? fromMatch[1] : 'unknown';
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

fastify.post('/decideUnsubscribe', async (request, reply) => {
  // The OpenAPI schema specifies requestBody content as text/plain
  // Fastify provides the raw body as a string if the content-type is text/plain 
  // and no complex body parser is overriding it.
  const rawEmail = request.body;

  if (typeof rawEmail !== 'string') {
    return reply.status(400).send({ error: 'Expected raw email text in request body' });
  }

  const email = extractEmail(rawEmail);
  const unsubscribe = shouldUnsubscribe(rawEmail);

  return {
    email: email,
    unsubscribe: unsubscribe
  };
});

// To handle text/plain bodies, we need to ensure Fastify doesn't try to parse it as JSON
// We add a content type parser for text/plain
fastify.addContentTypeParser('text/plain', { parseAs: 'string' }, (request, payload, done) => {
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