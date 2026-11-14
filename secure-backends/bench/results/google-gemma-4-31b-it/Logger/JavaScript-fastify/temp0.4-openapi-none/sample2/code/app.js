const fastify = require('fastify')({ logger: true });
const fs = require('fs');
const path = require('path');

const LOG_FILE = path.join(__dirname, 'logs.txt');

// POST /log - Log a message to the server
fastify.post('/log', async (request, reply) => {
  const { message } = request.body;

  if (typeof message !== 'string') {
    return reply.status(400).send({ error: 'Invalid input: message must be a string' });
  }

  // Append the message to logs.txt, each on a new line
  fs.appendFileSync(LOG_FILE, message + '\n', 'utf8');

  return reply.status(200).send();
});

// GET /logs - Retrieve all logged messages
fastify.get('/logs', async (request, reply) => {
  try {
    if (!fs.existsSync(LOG_FILE)) {
      return reply.status(200).type('text/plain').send('');
    }
    const data = fs.readFileSync(LOG_FILE, 'utf8');
    return reply.status(200).type('text/plain').send(data);
  } catch (err) {
    return reply.status(500).send({ error: 'Failed to read logs' });
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