const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { promisify } = require('util');

const execPromise = promisify(exec);

async function start() {
  const app = fastify({ logger: true });

  // Register multipart support for file uploads
  app.register(multipart);

  app.post('/concatenate', async (request, reply) => {
    const data = await request.file();
    
    if (!data || data.fieldname !== 'files') {
      return reply.status(400).send({ error: "Invalid input or missing files." });
    }

    const tempDir = path.join('/tmp', uuidv4());
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir);
    }

    const inputFiles = [];
    
    try {
      // Process the first file (since request.file() consumes the first stream)
      const firstFilePath = path.join(tempDir, `file_${inputFiles.length}.pdf`);
      await data.toFile(firstFilePath);
      inputFiles.push(firstFilePath);

      // Process remaining files in the multipart stream
      for await (const part of request.parts()) {
        if (part.file) {
          const filePath = path.join(tempDir, `file_${inputFiles.length}.pdf`);
          await part.toFile(filePath);
          inputFiles.push(filePath);
        }
      }

      if (inputFiles.length < 2) {
        // Cleanup and return error if not enough files to concatenate
        fs.rmSync(tempDir, { recursive: true, force: true });
        return reply.status(400).send({ error: "At least two PDF files are required for concatenation." });
      }

      const outputFilePath = path.join(tempDir, 'output.pdf');
      
      // Construct pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
      const filesArgs = inputFiles.join(' ');
      await execPromise(`pdfunite ${filesArgs} ${outputFilePath}`);

      // Set headers for PDF response
      reply.header('Content-Type', 'application/pdf');
      
      // Stream the file back to the client
      const fileStream = fs.createReadStream(outputFilePath);
      
      // We use a wrapper to ensure cleanup happens after the stream is finished
      return reply.send(fileStream);

    } catch (err) {
      app.log.error(err);
      return reply.status(500).send({ error: "An error occurred while processing the files." });
    } finally {
      // Note: In a production environment, you would use a more robust 
      // cleanup mechanism (like a cron job or delayed deletion) because 
      // reply.send(stream) is asynchronous. 
      // For this implementation, we trigger a cleanup after the response is sent.
      request.raw.on('finish', () => {
        fs.rmSync(tempDir, { recursive: true, force: true });
      });
    }
  });

  try {
    await app.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server listening on 0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
}

start();