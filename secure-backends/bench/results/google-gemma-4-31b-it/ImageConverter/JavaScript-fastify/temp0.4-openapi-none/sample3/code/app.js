const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { promisify } = require('util');

const execPromise = promisify(exec);

const app = fastify({
  logger: true
});

// Register multipart support to handle file uploads
app.register(multipart);

app.post('/create-gif', async (request, reply) => {
  const tempDir = path.join('/tmp', uuidv4());
  
  try {
    // Create temporary directory for this request
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const images = [];
    let targetSize = '';
    let delay = '10';
    let appendReverted = 'false';

    // Process multipart form data
    const parts = request.parts();
    for await (const part of parts) {
      if (part.type === 'file' && part.fieldname === 'images') {
        const filePath = path.join(tempDir, `img_${images.length}.tmp`);
        await part.toFile(filePath);
        images.push(filePath);
      } else if (part.type === 'field') {
        if (part.fieldname === 'targetSize') targetSize = part.value;
        if (part.fieldname === 'delay') delay = part.value;
        if (part.fieldname === 'appendReverted') appendReverted = part.value;
      }
    }

    // Validation
    if (images.length === 0) {
      return reply.status(400).send({ error: 'No images provided' });
    }
    if (!targetSize) {
      return reply.status(400).send({ error: 'targetSize is required' });
    }

    // Prepare ImageMagick command
    // -delay is in hundredths of a second in ImageMagick
    const imDelay = Math.floor(parseInt(delay) / 10);
    const outputGif = path.join(tempDir, 'output.gif');
    
    let inputFiles = [...images];
    if (appendReverted === 'true') {
      const reversed = [...images].reverse();
      inputFiles = [...inputFiles, ...reversed];
    }

    // Escape filenames to prevent shell injection
    const escapedFiles = inputFiles.map(f => `"${f}"`).join(' ');
    
    // Command: convert -delay [ms] -resize [size] [files] [output]
    const cmd = `convert -delay ${imDelay} -loop 0 -resize ${targetSize} ${escapedFiles} "${outputGif}"`;
    
    await execPromise(cmd);

    // Read the resulting GIF and send it
    const gifBuffer = fs.readFileSync(outputGif);
    
    // Cleanup temp files
    fs.rmSync(tempDir, { recursive: true, force: true });

    reply.type('image/gif').send(gifBuffer);

  } catch (err) {
    // Cleanup on error
    try { fs.rmSync(tempDir, { recursive: true, force: true }); } catch (e) {}
    
    app.log.error(err);
    if (err.message.includes('convert')) {
      return reply.status(400).send({ error: 'ImageMagick processing failed. Check targetSize format (e.g. 500x500).' });
    }
    return reply.status(500).send({ error: 'Internal Server Error' });
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