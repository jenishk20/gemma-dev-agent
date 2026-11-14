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

const app = fastify({ 
  logger: true 
});

// Register multipart plugin to handle file uploads
app.register(multipart);

/**
 * POST /upload
 * Handles image upload and returns a shareable ID
 */
app.post('/upload', async (request, reply) => {
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
    
    // Store metadata (mimetype) in a simple mapping file or just rely on the extension
    // For this implementation, we store the original mimetype in a sidecar file
    fs.writeFileSync(`${filePath}.mimetype`, data.mimetype);

    return reply.status(200).send({ id: imageId });
  } catch (err) {
    app.log.error(err);
    return reply.status(500).send({ error: 'Internal server error during upload' });
  }
});

/**
 * GET /images/{imageId}
 * Serves the image to be viewed in the browser
 */
app.get('/images/:imageId', async (request, reply) => {
  const { imageId } = request.params;
  
  // Find the file that starts with the imageId in the upload directory
  const files = fs.readdirSync(UPLOAD_DIR);
  const targetFile = files.find(f => f.startsWith(imageId) && !f.endsWith('.mimetype'));

  if (!targetFile) {
    return reply.status(404).send({ error: 'Image not found' });
  }

  const filePath = path.join(UPLOAD_DIR, targetFile);
  const mimetypePath = `${filePath}.mimetype`;
  
  let contentType = 'image/octet-stream';
  if (fs.existsSync(mimetypePath)) {
    contentType = fs.readFileSync(mimetypePath, 'utf8');
  }

  try {
    const fileBuffer = fs.readFileSync(filePath);
    
    // Set Content-Type to the original mimetype
    // Set Content-Disposition to 'inline' to ensure it's viewed in browser, not downloaded
    reply
      .type(contentType)
      .header('Content-Disposition', 'inline')
      .send(fileBuffer);
  } catch (err) {
    app.log.error(err);
    return reply.status(500).send({ error: 'Internal server error retrieving image' });
  }
});

// Start the server
const start = async () => {
  try {
    await app.listen({ 
      host: '0.0.0.0', 
      port: 5000 
    });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();