const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const { promisify } = require('util');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);

const app = fastify({
  logger: true
});

// Register multipart support to handle file uploads
app.register(multipart);

app.post('/convert', async (request, reply) => {
  const data = await request.file();
  
  if (!data) {
    return reply.status(400).send({ error: 'No file uploaded' });
  }

  if (data.mimetype !== 'application/pdf') {
    return reply.status(400).send({ error: 'Only PDF files are supported' });
  }

  // Create unique temporary paths for input and output
  const requestId = uuidv4();
  const inputPath = path.join(os.tmpdir(), `input_${requestId}.pdf`);
  const outputPath = path.join(os.tmpdir(), `output_${requestId}.txt`);

  try {
    // Save the uploaded buffer to a temporary file
    const writeStream = fs.createWriteStream(inputPath);
    await new Promise((resolve, reject) => {
      data.pipe(writeStream);
      data.on('end', resolve);
      data.on('error', reject);
      writeStream.on('finish', resolve);
      writeStream.on('error', reject);
    });

    // Use pdftotext utility from poppler-utils
    // -layout maintains the physical layout of the text
    await execPromise(`pdftotext -layout "${inputPath}" "${outputPath}"`);

    // Read the resulting text file
    const text = fs.readFileSync(outputPath, 'utf8');

    // Set content type to text/plain as per OpenAPI schema
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
    await app.listen({ 
      host: '0.0.0.0', 
      port: 5000 
    });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();