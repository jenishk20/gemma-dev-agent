const fastify = require('fastify')({ logger: true });
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

// Register multipart plugin to handle file uploads
fastify.register(multipart);

/**
 * POST /upload
 * Handles image upload and returns a shareable ID
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
    // Save the file stream to disk
    await pipeline(data.file, fs.createWriteStream(filePath));
    
    // Store the original mimetype in a sidecar file or database 
    // For this simple implementation, we store it in a JSON file named imageId.json
    const metaData = { mimetype: data.mimetype };
    fs.writeFileSync(path.join(UPLOAD_DIR, `${imageId}.json`), JSON.stringify(metaData));

    return reply.status(200).send({ id: imageId });
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
  const metaPath = path.join(UPLOAD_DIR, `${imageId}.json`);

  if (!fs.existsSync(metaPath)) {
    return reply.status(404).send({ error: 'Image not found' });
  }

  try {
    const meta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
    const files = fs.readdirSync(UPLOAD_DIR);
    const imageFile = files.find(f => f.startsWith(imageId) && !f.endsWith('.json'));

    if (!imageFile) {
      return reply.status(404).send({ error: 'Image file missing' });
    }

    const filePath = path.join(UPLOAD_DIR, imageFile);
    
    // Set Content-Type to the original mimetype so the browser renders it
    // Content-Disposition is NOT set to 'attachment' to ensure it's viewed in-browser
    reply.type(meta.mimetype);
    return reply.send(fs.createReadStream(filePath));
  } catch (err) {
    request.log.error(err);
    return reply.status(500).send({ error: 'Internal server error' });
  }
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ host: '0.0.0.0', port: 5000 });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();