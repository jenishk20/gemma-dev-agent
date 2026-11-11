const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { execFile } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const os = require('os');
const { promisify } = require('util');

const execFilePromise = promisify(execFile);

const app = fastify({
  logger: true
});

// Register multipart plugin to handle file uploads
app.register(multipart);

app.post('/convert', async (request, reply) => {
  try {
    // Extract the file from the multipart request
    const data = await request.file();
    
    if (!data || !data.file) {
      return reply.status(400).send({ error: 'No file uploaded' });
    }

    // Validate that the file is a PDF
    if (data.mimetype !== 'application/pdf') {
      return reply.status(400).send({ error: 'Uploaded file must be a PDF' });
    }

    // Create a temporary path to save the uploaded PDF
    const tempDir = os.tmpdir();
    const fileName = `${Date.now()}-${data.filename}`;
    const filePath = path.join(tempDir, fileName);

    // Write the stream to a temporary file
    const writeStream = await fs.open(filePath, 'w');
    const stream = writeStream.createWriteStream();
    
    await new Promise((resolve, reject) => {
      data.file.pipe(stream);
      data.file.on('end', resolve);
      data.file.on('error', reject);
    });

    try {
      // Use pdftotext utility from poppler-utils
      // -layout maintains the physical layout of the text
      // - specifies output to stdout (indicated by '-')
      const { stdout } = await execFilePromise('pdftotext', ['-layout', filePath, '-']);
      
      // Set response type to text/plain as per OpenAPI schema
      reply.type('text/plain');
      return stdout;
    } catch (err) {
      app.log.error(err);
      return reply.status(500).send({ error: 'Conversion failed' });
    } finally {
      // Cleanup: remove the temporary file
      await fs.unlink(filePath).catch(() => {});
    }

  } catch (error) {
    app.log.error(error);
    return reply.status(400).send({ error: 'Invalid input or missing file' });
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