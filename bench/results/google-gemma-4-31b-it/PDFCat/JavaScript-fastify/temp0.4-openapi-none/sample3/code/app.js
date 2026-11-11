const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);

const app = fastify({ logger: true });

// Register multipart support
app.register(multipart);

app.post('/concatenate', async (request, reply) => {
  const tempDir = path.join('/tmp', uuidv4());
  
  try {
    // Create a temporary directory for this request
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const parts = request.parts();
    const inputFiles = [];

    // Process the multipart stream
    for await (const part of parts) {
      if (part.file) {
        // We only care about the 'files' field as per schema
        if (part.fieldname === 'files') {
          const fileName = `${uuidv4()}.pdf`;
          const filePath = path.join(tempDir, fileName);
          
          // Save the buffer to a temporary file
          await new Promise((resolve, reject) => {
            const writeStream = fs.createWriteStream(filePath);
            part.file.pipe(writeStream);
            writeStream.on('finish', resolve);
            writeStream.on('error', reject);
          });
          
          inputFiles.push(filePath);
        } else {
          await part.file.consume();
        }
      } else {
        await part.consume();
      }
    }

    if (inputFiles.length === 0) {
      return reply.status(400).send({ error: "Invalid input or missing files." });
    }

    const outputFilePath = path.join(tempDir, 'output.pdf');
    
    // Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
    const command = `pdfunite ${inputFiles.map(f => `"${f}"`).join(' ')} "${outputFilePath}"`;
    
    try {
      await execPromise(command);
    } catch (err) {
      app.log.error(err);
      return reply.status(500).send({ error: "An error occurred while processing the files." });
    }

    // Read the resulting file and send it back
    const fileBuffer = fs.readFileSync(outputFilePath);
    
    // Clean up temporary files immediately after reading into memory
    fs.rmSync(tempDir, { recursive: true, force: true });

    reply.type('application/pdf').send(fileBuffer);

  } catch (error) {
    app.log.error(error);
    // Cleanup if error occurred during processing
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
    
    if (error.message === 'Invalid input or missing files.') {
      return reply.status(400).send({ error: error.message });
    }
    return reply.status(500).send({ error: "An error occurred while processing the files." });
  }
});

const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();