const fastify = require('fastify')({ logger: true });
const path = require('path');
const fs = require('fs');

const SONGS_DIRECTORY = '/var/songs';

// Define the schema for the /download endpoint to ensure validation
const downloadSchema = {
  body: {
    type: 'object',
    required: ['filename'],
    properties: {
      filename: { type: 'string' }
    }
  }
};

fastify.post('/download', { schema: downloadSchema }, async (request, reply) => {
  const { filename } = request.body;

  // Security: Prevent directory traversal attacks by extracting only the basename
  const safeFilename = path.basename(filename);
  const filePath = path.join(SONGS_DIRECTORY, safeFilename);

  try {
    // Check if file exists and is accessible
    await fs.promises.access(filePath, fs.constants.R_OK);

    // Set the correct content type for audio streaming
    reply.type('audio/mpeg');

    // Create a read stream and pipe it to the response
    const stream = fs.createReadStream(filePath);
    
    return reply.send(stream);
  } catch (err) {
    if (err.code === 'ENOENT') {
      return reply.code(404).send({ error: 'File does not exist' });
    }
    return reply.code(400).send({ error: 'Invalid input or server error' });
  }
});

const start = async () => {
  try {
    await fastify.listen({ 
      address: '0.0.0.0', 
      port: 5000 
    });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();