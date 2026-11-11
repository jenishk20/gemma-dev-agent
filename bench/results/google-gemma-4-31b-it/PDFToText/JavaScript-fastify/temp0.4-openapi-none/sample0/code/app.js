const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);
const unlinkPromise = promisify(fs.unlink);

const app = fastify({ 
  logger: true 
});

// Register multipart plugin to handle file uploads
app.register(multipart);

app.post('/convert', async (request, reply) => {
  // Get the file from the multipart stream
  const data = await request.file();
  
  if (!data || !data.file) {
    return reply.status(400).send({ error: 'No file uploaded' });
  }

  // Validate that the file is a PDF
  if (data.mimetype !== 'application/pdf' && !data.filename.toLowerCase().endsWith('.pdf')) {
    return reply.status(400).send({ error: 'Invalid file type. Please upload a PDF.' });
  }

  const tempFileName = `temp_${uuidv4()}.pdf`;
  const tempFilePath = path.join('/tmp', tempFileName);
  const tempOutputPath = path.join('/tmp', `${uuidv4()}.txt`);

  try {
    // Save the uploaded buffer to a temporary file
    await new Promise((resolve, reject) => {
      const writeStream = fs.createWriteStream(tempFilePath);
      data.file.pipe(writeStream);
      writeStream.on('finish', resolve);
      writeStream.on('error', reject);
    });

    // Use pdftotext from poppler-utils to extract text
    // -layout preserves the visual layout of the text
    await execPromise(`pdftotext -layout "${tempFilePath}" "${tempOutputPath}"`);

    // Read the resulting text file
    const text = fs.readFileSync(tempOutputPath, 'utf8');

    // Set content type to text/plain as per OpenAPI spec
    reply.type('text/plain').send(text);

  } catch (error) {
    app.log.error(error);
    reply.status(500).send({ error: 'Internal Server Error - Conversion failed' });
  } finally {
    // Cleanup temporary files
    try {
      if (fs.existsSync(tempFilePath)) await unlinkPromise(tempFilePath);
      if (fs.existsSync(tempOutputPath)) await unlinkPromise(tempOutputPath);
    } catch (cleanupError) {
      app.log.error(`Cleanup error: ${cleanupError}`);
    }
  }
});

// Start the server
const start = async () => {
  try {
    await app.listen({ 
      port: 5000, 
      host: '0.0.0.0' 
    });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();