const fastify = require('fastify')({ logger: true });
const fs = require('fs');
const path = require('path');

const SONGS_DIRECTORY = '/var/songs';

// Route to handle song streaming
fastify.post('/download', async (request, reply) => {
  const { filename } = request.body;

  // 400: Invalid input
  if (!filename || typeof filename !== 'string') {
    return reply.code(400).send({ error: 'Invalid input: filename is required' });
  }

  // Security: Prevent Directory Traversal attacks
  // Ensure the filename doesn't contain path separators or ".."
  const sanitizedFilename = path.basename(filename);
  if (sanitizedFilename !== filename) {
    return reply.code(400).send({ error: 'Invalid filename format' });
  }

  const filePath = path.join(SONGS_DIRECTORY, sanitizedFilename);

  try {
    // Check if file exists and is accessible
    await fs.promises.access(filePath, fs.constants.R_OK);

    // Set the correct content type for audio streaming
    reply.type('audio/mpeg');

    // Create a read stream and pipe it to the response
    const stream = fs.createReadStream(filePath);
    
    // Fastify supports returning a stream directly
    return reply.send(stream);
  } catch (err) {
    if (err.code === 'ENOENT') {
      // 404: File does not exist
      return reply.code(404).send({ error: 'File does not exist' });
    }
    // General server error
    return reply.code(500).send({ error: 'Internal server error' });
  }
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();