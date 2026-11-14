const fastify = require('fastify')({ logger: true });
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { promisify } = require('util');

const execPromise = promisify(exec);

// Register multipart support
fastify.register(multipart, {
  limits: {
    files: 10, // Limit number of files
  },
});

fastify.post('/concatenate', async (request, reply) => {
  const data = await request.file();
  
  if (!data) {
    return reply.status(400).send({ error: 'Invalid input or missing files.' });
  }

  // Since @fastify/multipart processes files sequentially in a stream, 
  // and the OpenAPI spec asks for multiple files in one request, 
  // we need to handle the multipart stream to collect all files.
  
  const parts = await request.saveRequestFiles();
  
  if (!parts || parts.length === 0) {
    return reply.status(400).send({ error: 'Invalid input or missing files.' });
  }

  const requestId = uuidv4();
  const tempDir = path.join('/tmp', requestId);
  
  try {
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir);
    }

    const inputFiles = [];
    
    // The saveRequestFiles() helper saves files to disk. 
    // We need to track the paths of the saved files.
    for (const file of parts) {
      // Ensure we only process PDF files
      if (path.extname(file.filename).toLowerCase() === '.pdf') {
        inputFiles.push(file.path);
      }
    }

    if (inputFiles.length === 0) {
      return reply.status(400).send({ error: 'No valid PDF files provided.' });
    }

    const outputFilePath = path.join(tempDir, 'concatenated.pdf');
    
    // Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
    const command = `pdfunite ${inputFiles.join(' ')} ${outputFilePath}`;
    
    await execPromise(command);

    // Read the resulting file and send it
    const pdfBuffer = fs.readFileSync(outputFilePath);
    
    // Clean up temp files immediately after reading into buffer
    fs.rmSync(tempDir, { recursive: true, force: true });

    reply.type('application/pdf').send(pdfBuffer);

  } catch (error) {
    fastify.log.error(error);
    
    // Cleanup on error
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }

    return reply.status(500).send({ error: 'An error occurred while processing the files.' });
  }
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();