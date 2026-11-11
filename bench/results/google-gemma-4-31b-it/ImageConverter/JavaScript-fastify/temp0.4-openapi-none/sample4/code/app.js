const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const { promisify } = require('util');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const execPromise = promisify(exec);

const app = fastify({ 
  logger: true 
});

// Register multipart support to handle file uploads
app.register(multipart);

app.post('/create-gif', async (request, reply) => {
  const tempDir = path.join('/tmp', uuidv4());
  
  try {
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const parts = request.parts();
    const imagesPaths = [];
    let targetSize = '';
    let delay = '10';
    let appendReverted = 'false';

    // Process the multipart stream
    for await (const part of parts) {
      if (part.file) {
        const fileName = `${uuidv4()}-${part.filename}`;
        const filePath = path.join(tempDir, fileName);
        await part.toFile(filePath);
        imagesPaths.push(filePath);
      } else {
        // Handle non-file fields
        const fieldName = part.fieldname;
        const value = await part.toBuffer().toString();
        if (fieldName === 'targetSize') targetSize = value;
        if (fieldName === 'delay') delay = value;
        if (fieldName === 'appendReverted') appendReverted = value;
      }
    }

    // Validation
    if (imagesPaths.length === 0) {
      return reply.status(400).send({ error: 'No images provided' });
    }
    if (!targetSize) {
      return reply.status(400).send({ error: 'targetSize is required' });
    }

    // Prepare ImageMagick command
    // -delay is in ticks (1/100th of a second), so ms / 10
    const delayTicks = Math.floor(parseInt(delay) / 10);
    const resizeParam = `-resize ${targetSize}`;
    
    let inputFiles = [...imagesPaths];
    if (appendReverted === 'true') {
      const reversed = [...imagesPaths].reverse();
      inputFiles = [...inputFiles, ...reversed];
    }

    const outputGifPath = path.join(tempDir, 'result.gif');
    
    // Command: convert -delay X -loop 0 [files] -resize WxH result.gif
    const cmd = `convert -delay ${delayTicks} -loop 0 ${inputFiles.join(' ')} ${resizeParam} ${outputGifPath}`;
    
    await execPromise(cmd);

    // Send the file
    const fileBuffer = fs.readFileSync(outputGifPath);
    reply.type('image/gif').send(fileBuffer);

  } catch (err) {
    app.log.error(err);
    return reply.status(500).send({ error: 'Internal Server Error: ' + err.message });
  } finally {
    // Cleanup temp files
    try {
      fs.rmSync(tempDir, { recursive: true, force: true });
    } catch (cleanupErr) {
      app.log.error('Cleanup error: ' + cleanupErr.message);
    }
  }
});

const start = async () => {
  try {
    await app.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();