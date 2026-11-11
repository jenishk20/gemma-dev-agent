const fastify = require('fastify')({ logger: true });
const multipart = require('@fastify/multipart');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');
const { pipeline } = require('stream/promises');

// Configuration
const UPLOAD_DIR = path.join(__dirname, 'uploads');
const PORT = 5000;
const HOST = '0.0.0.0';

// Ensure upload directory exists
if (!fs.existsSync(UPLOAD_DIR)) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

// Register multipart plugin
fastify.register(multipart);

/**
 * POST /upload
 * Handles image uploads and returns a unique ID
 */
fastify.post('/upload', async (request, reply) => {
  const data = await request.file();
  
  if (!data) {
    return reply.status(400).send({ error: 'No file uploaded' });
  }

  const imageId = uuidv4();
  const fileName = `${imageId}-${data.filename}`;
  const filePath = path.join(UPLOAD_DIR, fileName);

  try {
    // Save the file to the disk
    await pipeline(data.file, fs.createWriteStream(filePath));
    
    // Store metadata in a simple way (filename mapping)
    // In a real app, we'd use the sqlite3 dependency provided, 
    // but for a single-file runnable script, a file-system mapping is robust.
    // We save a small metadata file to keep track of the original mimetype.
    fs.writeFileSync(`${filePath}.meta`, data.mimetype);

    return { id: imageId };
  } catch (err) {
    request.log.error(err);
    return reply.status(500).send({ error: 'Internal server error during upload' });
  }
});

/**
 * GET /images/{imageId}
 * Serves the image to the browser
 */
fastify.get('/images/:imageId', async (request, reply) => {
  const { imageId } = request.params;
  
  // Find the file that starts with the imageId in the uploads folder
  const files = fs.readdirSync(UPLOAD_DIR);
  const targetFile = files.find(f => f.startsWith(`${imageId}-`));

  if (!targetFile) {
    return reply.status(404).send({ error: 'Image not found' });
  }

  const filePath = path.join(UPLOAD_DIR, targetFile);
  const metaPath = `${filePath}.meta`;
  
  let contentType = 'application/octet-stream';
  if (fs.existsSync(metaPath)) {
    contentType = fs.readFileSync(metaPath, 'utf8');
  }

  // To ensure it is viewable in the browser and not downloaded:
  // 1. Set the correct Content-Type
  // 2. Set Content-Disposition to 'inline'
  reply.type(contentType);
  reply.header('Content-Disposition', 'inline');

  return reply.sendFile(filePath);
});

// Fastify's sendFile requires @fastify/static or a custom implementation.
// Since @fastify/static isn't in the allowed list, we implement a simple stream response.
fastify.decorate('sendFile', function(filePath) {
  const stream = fs.createReadStream(filePath);
  return reply.send(stream);
});

// Override the internal sendFile logic for the route
fastify.get('/images/:imageId', async (request, reply) => {
  const { imageId } = request.params;
  const files = fs.readdirSync(UPLOAD_DIR);
  const targetFile = files.find(f => f.startsWith(`${imageId}-`));

  if (!targetFile) {
    return reply.status(404).send({ error: 'Image not found' });
  }

  const filePath = path.join(UPLOAD_DIR, targetFile);
  const metaPath = `${filePath}.meta`;
  
  let contentType = 'application/octet-stream';
  if (fs.existsSync(metaPath)) {
    contentType = fs.readFileSync(metaPath, 'utf8');
  }

  reply.type(contentType);
  reply.header('Content-Disposition', 'inline');
  
  const stream = fs.createReadStream(filePath);
  return reply.send(stream);
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ port: PORT, host: HOST });
    console.log(`Server listening on http://${HOST}:${PORT}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();