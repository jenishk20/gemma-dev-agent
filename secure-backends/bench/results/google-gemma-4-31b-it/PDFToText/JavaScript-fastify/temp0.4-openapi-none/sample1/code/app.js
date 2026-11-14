const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);

const app = fastify({
  logger: true
});

// Register multipart support for file uploads
app.register(multipart);

app.post('/convert', async (request, reply) => {
  const data = await request.file();
  
  if (!data) {
    return reply.status(400).send({ error: 'No file uploaded' });
  }

  if (data.mimetype !== 'application/pdf') {
    return reply.status(400).send({ error: 'Invalid file type. Please upload a PDF.' });
  }

  // Create a unique filename to avoid collisions during concurrent requests
  const fileId = uuidv4();
  const inputPath = path.join('/tmp', `${fileId}.pdf`);
  const outputPath = path.join('/tmp', `${fileId}.txt`);

  try {
    // Save the uploaded buffer to a temporary file
    await new Promise((resolve, reject) => {
      const writeStream = fs.createWriteStream(inputPath);
      data.pipe(writeStream);
      writeStream.on('finish', resolve);
      writeStream.on('error', reject);
    });

    // Use pdftotext utility from poppler-utils
    // -layout preserves the physical layout of the text
    await execPromise(`pdftotext -layout "${inputPath}" "${outputPath}"`);

    // Read the resulting text file
    const text = fs.readFileSync(outputPath, 'utf8');

    // Set content type to text/plain as per OpenAPI spec
    reply.type('text/plain').send(text);

  } catch (error) {
    app.log.error(error);
    reply.status(500).send({ error: 'Internal Server Error - Conversion failed' });
  } finally {
    // Cleanup temporary files
    try {
      if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
      if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
    } catch (cleanupError) {
      app.log.error('Cleanup error: ' + cleanupError.message);
    }
  }
});

const start = async () => {
  try {
    await app.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();