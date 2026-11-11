const fastify = require('fastify')({ logger: true });
const fs = require('fs');
const path = require('path');

const SONGS_DIRECTORY = '/var/songs';

fastify.post('/download', async (request, reply) => {
  const { filename } = request.body;

  if (!filename || typeof filename !== 'string') {
    return reply.status(400).send({ error: 'Invalid input: filename is required' });
  }

  // Prevent directory traversal attacks by extracting only the base name
  const safeFilename = path.basename(filename);
  const filePath = path.join(SONGS_DIRECTORY, safeFilename);

  // Check if file exists and is within the songs directory
  if (!fs.existsSync(filePath)) {
    return reply.status(404).send({ error: 'File does not exist' });
  }

  try {
    const stream = fs.createReadStream(filePath);
    
    // Set the content type to audio/mpeg as per OpenAPI spec
    reply.type('audio/mpeg');
    
    // Fastify supports returning a readable stream directly
    return reply.send(stream);
  } catch (err) {
    fastify.log.error(err);
    return reply.status(500).send({ error: 'Internal server error' });
  }
});

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