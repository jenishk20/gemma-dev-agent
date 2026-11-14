const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { promisify } = require('util');

const execPromise = promisify(exec);

const app = fastify({
  logger: false
});

// Register multipart support to handle file uploads
app.register(multipart);

app.post('/concatenate', async (request, reply) => {
  const tempDir = path.join('/tmp', uuidv4());
  
  try {
    // Create a temporary directory for this specific request
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const inputFiles = [];
    
    // Iterate through the multipart stream
    const parts = request.parts();
    for await (const part of parts) {
      if (part.fieldname === 'files') {
        const fileName = `${uuidv4()}.pdf`;
        const filePath = path.join(tempDir, fileName);
        
        // Save the buffer to a temporary file
        await new Promise((resolve, reject) => {
          const writeStream = fs.createWriteStream(filePath);
          part.pipe(writeStream);
          part.on('end', resolve);
          part.on('error', reject);
          writeStream.on('finish', resolve);
          writeStream.on('error', reject);
        });
        
        inputFiles.push(filePath);
      } else {
        // Consume other parts to avoid hanging the request
        await new Promise((resolve) => {
          part.on('end', resolve);
          part.pipe(require('stream').Cull()); // Dummy sink
        });
      }
    }

    if (inputFiles.length === 0) {
      return reply.status(400).send({ error: "Invalid input or missing files." });
    }

    if (inputFiles.length === 1) {
      // Only one file provided, just return it
      const fileBuffer = fs.readFileSync(inputFiles[0]);
      reply.type('application/pdf').send(fileBuffer);
      // Cleanup handled in finally block
      return;
    }

    const outputFilePath = path.join(tempDir, 'output.pdf');
    
    // Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
    const filesList = inputFiles.join(' ');
    const command = `pdfunite ${filesList} ${outputFilePath}`;
    
    try {
      await execPromise(command);
    } catch (err) {
      return reply.status(500).send({ error: "An error occurred while processing the files." });
    }

    const resultBuffer = fs.readFileSync(outputFilePath);
    reply.type('application/pdf').send(resultBuffer);

  } catch (error) {
    console.error(error);
    return reply.status(500).send({ error: "An error occurred while processing the files." });
  } finally {
    // Cleanup temporary files and directory
    try {
      fs.rmSync(tempDir, { recursive: true, force: true });
    } catch (cleanupError) {
      console.error('Cleanup error:', cleanupError);
    }
  }
});

const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on 0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();