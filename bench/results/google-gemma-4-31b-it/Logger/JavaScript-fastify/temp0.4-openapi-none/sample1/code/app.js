const fastify = require('fastify')({ logger: true });
const fs = require('fs');
const path = require('path');

const LOG_FILE = path.join(__dirname, 'logs.txt');

// Ensure the log file exists
if (!fs.existsSync(LOG_FILE)) {
  fs.writeFileSync(LOG_FILE, '', 'utf8');
}

// POST /log - Log a message
fastify.post('/log', async (request, reply) => {
  const { message } = request.body;

  if (typeof message !== 'string') {
    return reply.status(400).send({ error: 'Invalid input: message must be a string' });
  }

  // Append message to file with a newline
  fs.appendFileSync(LOG_FILE, message + '\n', 'utf8');
  
  return reply.status(200).send();
});

// GET /logs - Retrieve all logs
fastify.get('/logs', async (request, reply) => {
  try {
    const data = fs.readFileSync(LOG_FILE, 'utf8');
    reply.type('text/plain');
    return data;
  } catch (err) {
    return reply.status(500).send({ error: 'Could not read logs file' });
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