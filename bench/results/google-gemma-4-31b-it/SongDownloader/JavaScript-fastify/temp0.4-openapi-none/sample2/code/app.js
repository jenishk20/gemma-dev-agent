const fastify = require('fastify')({ logger: true });
const fs = require('fs');
const path = require('path');

const SONGS_DIRECTORY = '/var/songs';

// Route handler for /download
fastify.post('/download', async (request, reply) => {
  const { filename } = request.body;

  // 400: Invalid input if filename is missing
  if (!filename || typeof filename !== 'string') {
    return reply.code(400).send({ error: 'Invalid input: filename is required' });
  }

  // Security: Prevent Directory Traversal attacks
  // Ensure the filename does not contain path separators or ".."
  const sanitizedFilename = path.basename(filename);
  if (sanitizedFilename !== filename) {
    return reply.code(400).send({ error: 'Invalid filename provided' });
  }

  const filePath = path.join(SONGS_DIRECTORY, sanitizedFilename);

  // Check if file exists
  try {
    await fs.promises.access(filePath, fs.constants.R_OK);
  } catch (err) {
    return reply.code(404).send({ error: 'File does not exist' });
  }

  // Stream the file content
  const stream = fs.createReadStream(filePath);
  
  // Set content type to audio/mpeg as per OpenAPI spec
  reply.type('audio/mpeg');
  
  return reply.send(stream);
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