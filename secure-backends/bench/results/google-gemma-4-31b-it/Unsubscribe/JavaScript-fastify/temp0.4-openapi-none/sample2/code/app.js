const fastify = require('fastify')({ logger: true });

/**
 * Helper to extract the email address from the raw email text.
 * Looks for the 'From:' header pattern.
 */
function extractEmail(text) {
  const fromMatch = text.match(/^From:.*<(.+?)>/m) || text.match(/^From:\s*([^\s\r\n]+)/m);
  return fromMatch ? fromMatch[1] : null;
}

/**
 * Helper to determine if the email content suggests an unsubscribe request.
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
  // Fastify provides the raw body as a string if the content-type is text/plain 
  // and no specific parser is overriding it, but to be safe we handle the raw body.
  
  let rawEmail = '';
  
  // In Fastify, if the content-type is text/plain, request.body might be a string 
  // or we might need to read the stream. Since we aren't using a custom parser 
  // for text/plain in the basic setup, we can access the body.
  if (typeof request.body === 'string') {
    rawEmail = request.body;
  } else if (Buffer.isBuffer(request.body)) {
    rawEmail = request.body.toString('utf8');
  } else {
    // Fallback for cases where body might be parsed as object or missing
    rawEmail = JSON.stringify(request.body || '');
  }

  const email = extractEmail(rawEmail);
  const unsubscribe = shouldUnsubscribe(rawEmail);

  return reply.code(200).send({
    email: email || "unknown",
    unsubscribe: unsubscribe
  });
});

// Add a content type parser for text/plain to ensure request.body is a string
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