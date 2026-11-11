const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const { promisify } = require('util');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);
const fastifyInstance = fastify({ logger: true });

// Register multipart support to handle file uploads
fastifyInstance.register(multipart);

fastifyInstance.post('/concatenate', async (request, reply) => {
  const tempDir = path.join('/tmp', uuidv4());
  
  try {
    // Ensure temporary directory exists
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const parts = request.parts();
    const inputFiles = [];

    // Iterate through the multipart stream
    for await (const part of parts) {
      if (part.fieldname === 'files') {
        const fileName = `${uuidv4()}.pdf`;
        const filePath = path.join(tempDir, fileName);
        
        // Write the stream to a temporary file
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
        // Consume other fields to avoid hanging the request
        await new Promise((resolve) => part.on('end', resolve));
      }
    }

    if (inputFiles.length === 0) {
      return reply.status(400).send({ error: "Invalid input or missing files." });
    }

    const outputFilePath = path.join(tempDir, 'result.pdf');
    
    // Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
    const filesString = inputFiles.join(' ');
    const command = `pdfunite ${filesString} ${outputFilePath}`;
    
    try {
      await execPromise(command);
    } catch (err) {
      fastifyInstance.log.error(err);
      return reply.status(500).send({ error: "An error occurred while processing the files." });
    }

    // Read the resulting PDF and send it back
    const pdfBuffer = fs.readFileSync(outputFilePath);
    
    // Cleanup temporary files
    fs.rmSync(tempDir, { recursive: true, force: true });

    reply.type('application/pdf').send(pdfBuffer);

  } catch (error) {
    fastifyInstance.log.error(error);
    // Cleanup in case of failure
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
    
    if (error.code === 'ENOENT') {
      return reply.status(400).send({ error: "Invalid input or missing files." });
    }
    return reply.status(500).send({ error: "An error occurred while processing the files." });
  }
});

const start = async () => {
  try {
    await fastifyInstance.listen({ address: '0.0.0.0', port: 5000 });
  } catch (err) {
    fastifyInstance.log.error(err);
    process.exit(1);
  }
};

start();