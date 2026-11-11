const fastify = require('fastify')({ logger: true });
const fs = require('fs');
const path = require('path');

const SONGS_DIRECTORY = '/var/songs';

// Route handler for /download
fastify.post('/download', async (request, reply) => {
  const { filename } = request.body;

  // 400: Invalid input
  if (!filename || typeof filename !== 'string') {
    return reply.status(400).send({ error: 'Invalid input: filename is required' });
  }

  // Prevent directory traversal attacks by extracting only the base name
  const safeFilename = path.basename(filename);
  const filePath = path.join(SONGS_DIRECTORY, safeFilename);

  try {
    // Check if file exists and is accessible
    await fs.promises.access(filePath, fs.constants.F_OK);

    // Set content type to audio/mpeg as per OpenAPI spec
    reply.type('audio/mpeg');

    // Create a read stream to pipe the file content to the response
    const stream = fs.createReadStream(filePath);
    
    return reply.send(stream);
  } catch (err) {
    // 404: File does not exist
    return reply.status(404).send({ error: 'File does not exist' });
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