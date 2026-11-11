const fastify = require('fastify')({ logger: true });
const fs = require('fs/promises');
const path = require('path');

const LOG_FILE = path.join(__dirname, 'logs.txt');

// POST /log - Log a message
fastify.post('/log', async (request, reply) => {
  const { message } = request.body;

  if (!message || typeof message !== 'string') {
    return reply.status(400).send({ error: 'Invalid request body. "message" string is required.' });
  }

  try {
    // Append the message followed by a newline to the text file
    await fs.appendFile(LOG_FILE, message + '\n', 'utf8');
    return reply.status(200).send();
  } catch (err) {
    fastify.log.error(err);
    return reply.status(500).send({ error: 'Internal Server Error' });
  }
});

// GET /logs - Retrieve all logs
fastify.get('/logs', async (request, reply) => {
  try {
    // Read the entire file content
    const data = await fs.readFile(LOG_FILE, 'utf8');
    reply.type('text/plain');
    return data;
  } catch (err) {
    // If file doesn't exist yet, return empty string
    if (err.code === 'ENOENT') {
      reply.type('text/plain');
      return '';
    }
    fastify.log.error(err);
    return reply.status(500).send({ error: 'Internal Server Error' });
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