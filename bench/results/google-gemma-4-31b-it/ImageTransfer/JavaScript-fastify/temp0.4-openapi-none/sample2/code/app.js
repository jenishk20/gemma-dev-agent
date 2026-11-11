const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');
const { pipeline } = require('stream/promises');

const UPLOAD_DIR = path.join(__dirname, 'uploads');

// Ensure upload directory exists
if (!fs.existsSync(UPLOAD_DIR)) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

const server = fastify({ 
  logger: true 
});

// Register multipart plugin to handle file uploads
server.register(multipart, {
  limits: {
    files: 1, // Only allow one file per request as per schema
  }
});

/**
 * POST /upload
 * Handles image upload and returns a unique ID
 */
server.post('/upload', async (request, reply) => {
  const data = await request.file();
  
  if (!data) {
    return reply.status(400).send({ error: 'No file uploaded' });
  }

  const imageId = uuidv4();
  const fileName = `${imageId}-${data.filename}`;
  const filePath = path.join(UPLOAD_DIR, fileName);

  try {
    // Save the file to the filesystem
    await pipeline(data.file, fs.createWriteStream(filePath));
    
    // Store the original mimetype in a sidecar file or a simple map
    // For this implementation, we store it in a simple .meta file to persist across restarts
    await fs.promises.writeFile(`${filePath}.meta`, data.mimetype);

    return reply.status(200).send({ id: imageId });
  } catch (err) {
    server.log.error(err);
    return reply.status(500).send({ error: 'Internal server error during upload' });
  }
});

/**
 * GET /images/{imageId}
 * Serves the image file with the correct mimetype to ensure browser viewing
 */
server.get('/images/:imageId', async (request, reply) => {
  const { imageId } = request.params;

  // Find the file that starts with the imageId in the uploads directory
  const files = await fs.promises.readdir(UPLOAD_DIR);
  const targetFile = files.find(f => f.startsWith(imageId) && !f.endsWith('.meta'));

  if (!targetFile) {
    return reply.status(404).send({ error: 'Image not found' });
  }

  const filePath = path.join(UPLOAD_DIR, targetFile);
  const metaPath = `${filePath}.meta`;

  try {
    let contentType = 'image/generic';
    if (fs.existsSync(metaPath)) {
      contentType = await fs.promises.readFile(metaPath, 'utf8');
    }

    // Set Content-Type to the original mimetype
    // Set Content-Disposition to inline to prevent forced download
    reply.type(contentType);
    reply.header('Content-Disposition', 'inline');

    return reply.sendFile(filePath);
  } catch (err) {
    server.log.error(err);
    return reply.status(500).send({ error: 'Internal server error retrieving image' });
  }
});

// Custom sendFile implementation since Fastify doesn't have a built-in sendFile 
// like Express unless @fastify/static is used (which is not in the allowed list).
// We override the reply.sendFile behavior using a stream.
server.decorateRequest('sendFile', async function (filePath) {
  const stream = fs.createReadStream(filePath);
  return reply.send(stream);
});

// Since we can't use @fastify/static, we manually handle the stream in the route
// Re-defining the route handler to use standard streams
server.route({
  method: 'GET',
  url: '/images/:imageId',
  handler: async (request, reply) => {
    const { imageId } = request.params;
    const files = await fs.promises.readdir(UPLOAD_DIR);
    const targetFile = files.find(f => f.startsWith(imageId) && !f.endsWith('.meta'));

    if (!targetFile) {
      return reply.status(404).send({ error: 'Image not found' });
    }

    const filePath = path.join(UPLOAD_DIR, targetFile);
    const metaPath = `${filePath}.meta`;

    try {
      let contentType = 'application/octet-stream';
      if (fs.existsSync(metaPath)) {
        contentType = await fs.promises.readFile(metaPath, 'utf8');
      }

      reply.type(contentType);
      reply.header('Content-Disposition', 'inline');
      
      const stream = fs.createReadStream(filePath);
      return reply.send(stream);
    } catch (err) {
      return reply.status(500).send({ error: 'Internal server error' });
    }
  }
});

const start = async () => {
  try {
    await server.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    server.log.error(err);
    process.exit(1);
  }
};

start();