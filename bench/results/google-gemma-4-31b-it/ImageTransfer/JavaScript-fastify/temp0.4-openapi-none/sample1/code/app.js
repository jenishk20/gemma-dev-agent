const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');

const pipeline = promisify(require('stream').pipeline);

async function start() {
  const app = fastify({ logger: true });

  // Register multipart support for file uploads
  app.register(multipart);

  const UPLOAD_DIR = path.join(__dirname, 'uploads');

  // Ensure upload directory exists
  if (!fs.existsSync(UPLOAD_DIR)) {
    fs.mkdirSync(UPLOAD_DIR, { recursive: true });
  }

  // POST /upload - Upload an image
  app.post('/upload', async (request, reply) => {
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
      
      // We store the original mimetype in a sidecar file or just rely on the extension
      // For this implementation, we'll save the mimetype in a simple mapping file or just use the file extension
      // To be robust, we save the mimetype in a metadata file
      fs.writeFileSync(`${filePath}.mimetype`, data.mimetype);

      return reply.status(200).send({ id: imageId });
    } catch (err) {
      app.log.error(err);
      return reply.status(500).send({ error: 'Internal server error during upload' });
    }
  });

  // GET /images/{imageId} - Serve the image
  app.get('/images/:imageId', async (request, reply) => {
    const { imageId } = request.params;

    try {
      // Find the file that starts with the imageId in the upload directory
      const files = fs.readdirSync(UPLOAD_DIR);
      const foundFile = files.find(f => f.startsWith(imageId) && !f.endsWith('.mimetype'));

      if (!foundFile) {
        return reply.status(404).send({ error: 'Image not found' });
      }

      const filePath = path.join(UPLOAD_DIR, foundFile);
      const mimetypePath = `${filePath}.mimetype`;
      
      let contentType = 'application/octet-stream';
      if (fs.existsSync(mimetypePath)) {
        contentType = fs.readFileSync(mimetypePath, 'utf8');
      }

      // To ensure it's viewable in browser and not recommended for download:
      // 1. Set Content-Type correctly
      // 2. Set Content-Disposition to inline
      reply.type(contentType);
      reply.header('Content-Disposition', 'inline');

      return reply.sendFile(filePath);
    } catch (err) {
      app.log.error(err);
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
}

start();