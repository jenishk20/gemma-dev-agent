const fastify = require('fastify')({ 
  logger: true 
});

/**
 * Helper to extract the email address from the raw MIME email string.
 * Looks for the 'From:' header.
 */
function extractEmail(rawBody) {
  const fromMatch = rawBody.match(/^From:.*<(.+?)>/m) || rawBody.match(/^From:\s*([^\s\r\n]+)/m);
  return fromMatch ? fromMatch[1] : null;
}

/**
 * Helper to determine if the email contains unsubscribe keywords.
 */
function shouldUnsubscribe(rawBody) {
  const keywords = [
    "unsubscribe", 
    "remove me", 
    "deregister me", 
    "stop sending me", 
    "delete me"
  ];
  const lowerBody = rawBody.toLowerCase();
  return keywords.some(keyword => lowerBody.includes(keyword));
}

// Fastify by default parses JSON and Form-urlencoded. 
// To handle 'text/plain' raw bodies, we need to access the raw request stream 
// or use a plugin. Since we are limited to the provided packages, 
// we can use a custom content type parser or read the stream.

fastify.addContentTypeParser('text/plain', { parseAs: 'string' }, (request, payload, done) => {
  let data = '';
  payload.on('data', chunk => {
    data += chunk;
  });
  payload.on('end', () => {
    done(null, data);
  });
});

fastify.post('/decideUnsubscribe', async (request, reply) => {
  const rawEmail = request.body;

  if (typeof rawEmail !== 'string') {
    return reply.status(400).send({ error: 'Expected raw email text in request body' });
  }

  const email = extractEmail(rawEmail);
  const unsubscribe = shouldUnsubscribe(rawEmail);

  return reply.status(200).send({
    email: email || 'unknown',
    unsubscribe: unsubscribe
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